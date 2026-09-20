"""Answer one call, record 10s, report exactly what arrived. No pipeline.

Diagnostic for a call where the caller cannot be heard. It touches nothing but
ARI -- no recognition, no synthesis, no turn loop -- so the byte count it
reports separates a media path problem from anything in the pipeline. Zero
bytes means no RTP reached Asterisk at all.

    uv run python scripts/rtp_probe.py

Stop `make voice` first: both subscribe to the same Stasis app and would
compete for the call. Dial in when it says it is waiting, and talk
continuously -- the silence timeout is set to the full duration, so it will not
cut off early.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Run as a script, not a module, so the project root is not already on the
# path and `api` and `voice_service` would not import.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.config.config import settings  # noqa: E402
from voice_service.ari import AriClient  # noqa: E402

RECORD_SECONDS = 10
# u-law is one byte per sample, so this is what a full recording should weigh.
TELEPHONY_RATE = 8000

logging.basicConfig(level="INFO", format="%(asctime)s %(message)s")
log = logging.getLogger("probe")


async def main() -> None:
    async with AriClient(
        settings.ARI_BASE_URL,
        settings.ARI_USERNAME,
        settings.ARI_PASSWORD,
        settings.ARI_APP_NAME,
    ) as ari:
        log.info("waiting for a call -- dial in now and TALK CONTINUOUSLY")
        async for event in ari.events():
            if event.get("type") != "StasisStart":
                continue

            channel_id = event["channel"]["id"]
            log.info("call %s: answering", channel_id)
            await ari.answer(channel_id)
            await asyncio.sleep(1)

            name = f"probe-{channel_id}"
            log.info("recording %ds -- TALK NOW", RECORD_SECONDS)
            # Silence timeout equal to the duration, so a quiet moment does
            # not end the recording early and confuse the result.
            await ari.record(channel_id, name, RECORD_SECONDS, RECORD_SECONDS)
            await asyncio.sleep(RECORD_SECONDS + 2)

            audio = await ari.stored_recording(name)
            log.info(
                "RESULT: %d bytes (%.2fs of audio)",
                len(audio),
                len(audio) / TELEPHONY_RATE,
            )
            if audio:
                destination = ROOT / "var" / "voice" / "probe.ulaw"
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(audio)
                log.info("saved %s", destination)
            else:
                log.info("no RTP reached Asterisk -- the media path is the problem")

            await ari.delete_recording(name)
            await ari.hangup(channel_id)
            return


if __name__ == "__main__":
    asyncio.run(main())
