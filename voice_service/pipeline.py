"""The voice pipeline: speech in, speech out.

Speech recognition and synthesis run locally (Vosk and Piper) so a call works
end to end with no API key and no network. The middle stage is still a stub:
`llm` returns a canned line, because which provider answers the caller is not
decided yet. Replace that body, not the signatures.

Audio is 8 kHz mono u-law throughout, which is what the trunk carries -- see
voice_service/audio.py for the conversions each model needs.
"""

import logging

from voice_service.local_speech import stt as local_stt
from voice_service.local_speech import tts as local_tts

logger = logging.getLogger("voice.pipeline")

# Said when the caller's speech came through as nothing -- silence, or noise
# the recogniser could not resolve into words.
NO_SPEECH_REPLY = "Sorry, I didn't catch that. Could you say it again?"


async def stt(audio: bytes) -> str:
    """Transcribe caller audio to text."""
    return await local_stt(audio)


async def llm(text: str) -> str:
    """Turn what the caller said into what to say back.

    Stub: echoes the caller so a test call proves recognition end to end, and
    the reply audibly changes with what was actually said.
    """
    if not text.strip():
        return NO_SPEECH_REPLY
    logger.info("llm: prompt=%r", text)
    return f"You said: {text}. This is a test response from Me."


async def tts(text: str) -> bytes:
    """Render a reply as 8 kHz u-law audio for the trunk."""
    return await local_tts(text)
