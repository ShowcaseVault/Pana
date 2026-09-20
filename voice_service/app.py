"""The voice service: drives an AI conversation on a live call over ARI.

Connects to Asterisk, subscribes to the `pana-voice` Stasis app, and runs one
turn loop per call: record the caller, transcribe, generate a reply, speak it.

A turn is processed in chunks rather than as one block. The model writes the
reply a sentence at a time and each sentence is synthesised and played while
the next is still being written, so the caller hears the first words in about
the time that first sentence takes instead of waiting for the whole answer.
Playback is still sequential -- Asterisk plays one file per sentence, in order
-- so the chunking buys time to first word, not overlapping audio.

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
from voice_service.pipeline import NO_SPEECH_REPLY, llm_stream, stt, tts_stream

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
# Turns kept as context for the model. A phone call does not refer back far,
# and every kept turn is tokens on the critical path of the next reply.
HISTORY_TURNS = 12

GREETING = "Hello, thanks for calling Pana. How can I help?"


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
        # The conversation so far, in the shape the model takes.
        self.history: list[dict[str, str]] = []

    def _remember(self, role: str, content: str) -> None:
        """Add a turn to the history, dropping the oldest once it is full."""
        if not content.strip():
            return
        self.history.append({"role": role, "content": content})
        del self.history[:-HISTORY_TURNS]

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

    async def _play_file(self, audio: bytes) -> bool:
        """Hand one piece of u-law audio to Asterisk and wait for it to finish."""
        # Asterisk plays from a file by path, not from bytes, so the audio is
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
            # One file per sentence would otherwise accumulate for the life of
            # the host; the audio is worthless once played.
            path.unlink(missing_ok=True)

    async def _speak(self, text: str) -> bool:
        """Synthesise `text` and play it. False if the call ended."""
        audio = b"".join([chunk async for chunk in tts_stream(text)])
        if not audio:
            logger.warning("call %s: tts produced no audio", self.channel_id)
            return True
        return await self._play_file(audio)

    async def _respond(self) -> bool:
        """Generate a reply to the history and speak it as it is written.

        Synthesis of the next sentence is started before the current one has
        finished playing, so the gap between sentences is whatever synthesis
        did not manage to hide behind playback, rather than its full cost.
        """
        spoken: list[str] = []
        pending: asyncio.Task[bytes] | None = None

        async def synthesise(sentence: str) -> bytes:
            return b"".join([chunk async for chunk in tts_stream(sentence)])

        try:
            async for sentence in llm_stream(self.history):
                # Play what the previous pass synthesised, then queue this
                # sentence so it is made while that one is on the wire.
                if pending is not None and not await self._play_file(await pending):
                    return False
                if self.hung_up.is_set():
                    return False
                spoken.append(sentence)
                pending = asyncio.create_task(synthesise(sentence))

            if pending is not None:
                audio = await pending
                pending = None
                if audio and not await self._play_file(audio):
                    return False
        finally:
            # A reply abandoned mid-stream must not leave synthesis running.
            if pending is not None:
                pending.cancel()
            self._remember("assistant", " ".join(spoken))

        return not self.hung_up.is_set()

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

        if not await self._speak(GREETING):
            return
        self._remember("assistant", GREETING)

        while not self.hung_up.is_set():
            audio = await self._listen()
            if self.hung_up.is_set():
                break
            if not audio:
                logger.info("call %s: nothing recorded, ending", self.channel_id)
                break
            text = await stt(audio)
            if not text.strip():
                # Nothing recognised: re-prompt without polluting the history
                # with an empty turn the model would have to interpret.
                if not await self._speak(NO_SPEECH_REPLY):
                    break
                continue
            self._remember("user", text)
            if not await self._respond():
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
