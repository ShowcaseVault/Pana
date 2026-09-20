"""Groq-hosted speech recognition for the voice pipeline.

Whisper on Groq is the recogniser for a live call: the same provider that
answers the caller also transcribes them, so a call needs one key rather than
two. The turbo model is the default because a call is latency-bound -- a
better transcript that lands a second later is a worse call.

Call audio arrives as 8 kHz u-law, which the API will not take directly, so it
is wrapped in a WAV container here. The bytes are not resampled: Whisper
resamples server-side, and upsampling first would only make the upload bigger
without adding anything that was not in the 8 kHz original.
"""

import io
import logging
import wave

from api.config.config import settings
from api.connections import get_groq_client
from voice_service.audio import CHANNELS, SAMPLE_WIDTH, TELEPHONY_RATE, ulaw_to_pcm

logger = logging.getLogger("voice.groq")

# Below this, the "recording" is silence or a click: a turn no recogniser will
# resolve into words. One second of 8 kHz u-law is 8000 bytes.
MIN_AUDIO_BYTES = 1600


def _to_wav(ulaw: bytes) -> bytes:
    """Wrap u-law call audio in a WAV container, as 16-bit PCM at 8 kHz."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as target:
        target.setnchannels(CHANNELS)
        target.setsampwidth(SAMPLE_WIDTH)
        target.setframerate(TELEPHONY_RATE)
        target.writeframes(ulaw_to_pcm(ulaw))
    return buffer.getvalue()


async def stt(audio: bytes) -> str:
    """Transcribe one turn of 8 kHz u-law call audio."""
    if len(audio) < MIN_AUDIO_BYTES:
        logger.info(
            "stt: %d bytes (%.2fs) is below the floor, treating as silence",
            len(audio),
            len(audio) / TELEPHONY_RATE,
        )
        return ""

    response = await get_groq_client().audio.transcriptions.create(
        # The name is what the API reads the container format from; the bytes
        # are what it transcribes.
        file=("turn.wav", _to_wav(audio)),
        model=settings.STT_MODEL_REALTIME,
        response_format="text",
        temperature=0.0,
    )
    # `response_format="text"` returns the transcript itself, not an object.
    text = (response if isinstance(response, str) else response.text).strip()
    logger.info("stt: %r", text)
    return text
