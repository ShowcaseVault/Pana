"""The voice service: drives an AI conversation on a live call over ARI.

Connects to Asterisk, subscribes to the `pana-voice` Stasis app, and runs one
turn loop per call: record the caller, transcribe, generate a reply, speak it.

Turns are record-then-respond, which needs nothing beyond ARI itself. The end
state is an `externalMedia` channel forking RTP, which is what makes barge-in
possible; the pipeline's stt/llm/tts seams do not change when that arrives.
See docs/telephony.md.

Run with: make voice
"""

import asyncio
import logging
import uuid
from pathlib import Path

from api.config.config import settings
from voice_service.ari import AriClient
from voice_service.pipeline import llm, stt, tts

logger = logging.getLogger("voice")

# One caller turn. The whole call is already capped by TIMEOUT(absolute) in the
# dialplan, so this only shapes how long a single utterance may run.
MAX_TURN_SECONDS = 15
# Silence that ends a turn: short enough to feel responsive, long enough to
# survive a mid-sentence pause.
SILENCE_SECONDS = 2
# Backstop for waiting on an Asterisk operation. Reached only if the event that
# should end it never arrives, which would otherwise hang the turn loop.
EVENT_TIMEOUT = MAX_TURN_SECONDS + 10


class CallSession:
    """One call: the turn loop, and the events Asterisk sends back to it.

    Recording and playback finish asynchronously -- Asterisk reports them as
    events on the app's websocket, not as a response to the request that
    started them. The loop therefore starts an operation and waits on the
    matching event, rather than sleeping for a guessed duration.
    """

    def __init__(self, ari: AriClient, channel_id: str) -> None:
        self.ari = ari
        self.channel_id = channel_id
        self.recording_done = asyncio.Event()
        self.playback_done = asyncio.Event()
        self.hung_up = asyncio.Event()

    async def _wait(self, event: asyncio.Event, what: str) -> bool:
        """Wait for `event`, or for the caller to hang up. False if it timed out."""
        waiters = [asyncio.create_task(event.wait()), asyncio.create_task(self.hung_up.wait())]
        try:
            done, _ = await asyncio.wait(
                waiters, timeout=EVENT_TIMEOUT, return_when=asyncio.FIRST_COMPLETED
            )
        finally:
            for task in waiters:
                task.cancel()
        if not done:
            logger.warning("call %s: timed out waiting for %s", self.channel_id, what)
            return False
        return not self.hung_up.is_set()

    async def _speak(self, text: str) -> bool:
        """Synthesise `text`, hand the file to Asterisk, and wait for playback."""
        audio = await tts(text)
        if not audio:
            logger.warning("call %s: tts produced no audio", self.channel_id)
            return True

        # Asterisk plays from a file by path, not from bytes, so the reply is
        # written to the directory shared with the container. `.ulaw` is a
        # headerless format Asterisk reads by extension, and the audio is
        # already at the trunk's rate, so playback does not transcode.
        name = f"{self.channel_id}-{uuid.uuid4().hex[:8]}"
        path = Path(settings.VOICE_TTS_DIR) / f"{name}.ulaw"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(audio)

        try:
            self.playback_done.clear()
            # A `sound:` URI takes the path without its extension.
            media = f"sound:{settings.VOICE_TTS_CONTAINER_DIR}/{name}"
            if await self.ari.play(self.channel_id, media) is None:
                return False
            return await self._wait(self.playback_done, "playback")
        finally:
            # One file per turn would otherwise accumulate for the life of the
            # host; the audio is worthless once played.
            path.unlink(missing_ok=True)

    async def _listen(self) -> bytes:
        """Record the caller's next utterance and return it as u-law."""
        name = f"pana-{self.channel_id}-{uuid.uuid4().hex[:8]}"
        self.recording_done.clear()
        await self.ari.record(self.channel_id, name, MAX_TURN_SECONDS, SILENCE_SECONDS)
        await self._wait(self.recording_done, "recording")

        audio = await self.ari.stored_recording(name)
        await self.ari.delete_recording(name)
        return audio

    async def run(self) -> None:
        """Greet the caller, then trade turns until they hang up."""
        await self.ari.answer(self.channel_id)
        logger.info("call %s: answered", self.channel_id)

        if not await self._speak("Hello, thanks for calling Pana. How can I help?"):
            return

        while not self.hung_up.is_set():
            audio = await self._listen()
            if self.hung_up.is_set():
                break
            if not audio:
                logger.info("call %s: nothing recorded, ending", self.channel_id)
                break
            if not await self._speak(await llm(await stt(audio))):
                break

        logger.info("call %s: conversation finished", self.channel_id)


async def handle_call(session: CallSession) -> None:
    """Run one call, making sure a failure ends that call and nothing else."""
    try:
        await session.run()
    except asyncio.CancelledError:
        logger.info("call %s: handler cancelled", session.channel_id)
        raise
    except Exception:
        # One failing call must not take the service down with it.
        logger.exception("call %s: handler failed", session.channel_id)
    finally:
        if not session.hung_up.is_set():
            await session.ari.hangup(session.channel_id)


async def run() -> None:
    """Subscribe to Stasis and dispatch a session per call."""
    if not settings.ARI_PASSWORD:
        raise RuntimeError(
            "ARI_PASSWORD is not set. Add it to .env, the same value Asterisk "
            "reads (see .env.example), and generate one with: openssl rand -hex 32"
        )

    sessions: dict[str, CallSession] = {}
    tasks: dict[str, asyncio.Task[None]] = {}

    async with AriClient(
        settings.ARI_BASE_URL,
        settings.ARI_USERNAME,
        settings.ARI_PASSWORD,
        settings.ARI_APP_NAME,
    ) as ari:
        logger.info("voice service ready, waiting for calls")
        async for event in ari.events():
            kind = event.get("type")
            channel_id = (
                event.get("channel", {}).get("id")
                or event.get("playback", {}).get("target_uri", "").removeprefix("channel:")
                or event.get("recording", {}).get("target_uri", "").removeprefix("channel:")
            )
            if not channel_id:
                continue
            session = sessions.get(channel_id)

            if kind == "StasisStart":
                logger.info("call %s: entered Stasis", channel_id)
                session = CallSession(ari, channel_id)
                sessions[channel_id] = session
                tasks[channel_id] = asyncio.create_task(handle_call(session))
            elif session is None:
                continue
            elif kind == "StasisEnd":
                logger.info("call %s: left Stasis", channel_id)
                session.hung_up.set()
                sessions.pop(channel_id, None)
                task = tasks.pop(channel_id, None)
                if task is not None:
                    task.cancel()
            elif kind in ("RecordingFinished", "RecordingFailed"):
                session.recording_done.set()
            elif kind in ("PlaybackFinished", "PlaybackFailed"):
                session.playback_done.set()


def main() -> None:
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("voice service stopped")
    except RuntimeError as error:
        # Configuration problems are for the operator to fix, so print the fix
        # rather than a traceback through asyncio.
        raise SystemExit(f"voice service cannot start: {error}") from None


if __name__ == "__main__":
    main()
