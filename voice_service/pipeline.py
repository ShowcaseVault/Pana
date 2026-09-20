"""The voice pipeline: speech in, speech out.

Three stages, each behind one function, each with a hosted provider and a
local fallback:

    stt   Groq (Whisper turbo)   or Vosk, offline
    llm   Groq (chat)            or a canned reply
    tts   NVIDIA Magpie          or Piper, offline

Which one runs is a setting, not an import: VOICE_STT_PROVIDER,
VOICE_LLM_PROVIDER and VOICE_TTS_PROVIDER, each of which takes "local" to force
the offline path. A hosted stage that raises falls back to local for that turn
rather than dropping the call -- a worse answer beats a dead line.

Two of the stages also stream. `llm_stream` yields the reply a sentence at a
time and `tts_stream` yields audio as it is synthesised, which is what lets the
caller hear the first sentence while the rest is still being written. The
non-streaming forms remain for anything that wants the whole result.

Audio is 8 kHz mono u-law at every seam, which is what the trunk carries -- see
voice_service/audio.py for the conversions each model needs.
"""

import logging
from collections.abc import AsyncIterator

from api.config.config import settings
from voice_service.local_speech import stt as local_stt
from voice_service.local_speech import tts as local_tts

logger = logging.getLogger("voice.pipeline")

# Said when the caller's speech came through as nothing -- silence, or noise
# the recogniser could not resolve into words.
NO_SPEECH_REPLY = "Sorry, I didn't catch that. Could you say it again?"

# Said when generation itself failed. The caller hears a sentence rather than
# silence, and the turn loop keeps going.
FALLBACK_REPLY = "Sorry, I'm having trouble answering right now. Could you try again?"


async def stt(audio: bytes) -> str:
    """Transcribe one turn of caller audio."""
    if settings.VOICE_STT_PROVIDER == "local":
        return await local_stt(audio)

    from voice_service.providers.groq_speech import stt as groq_stt

    try:
        return await groq_stt(audio)
    except Exception:
        logger.exception("stt: Groq failed, falling back to the local recogniser")
        return await local_stt(audio)


async def llm_stream(history: list[dict[str, str]]) -> AsyncIterator[str]:
    """Yield the reply to `history` sentence by sentence.

    `history` is the conversation in OpenAI message shape, oldest first, ending
    with the caller's latest turn.
    """
    if not history or not history[-1].get("content", "").strip():
        yield NO_SPEECH_REPLY
        return

    if settings.VOICE_LLM_PROVIDER == "local":
        yield FALLBACK_REPLY
        return

    from voice_service.providers.groq_llm import llm_stream as groq_stream

    spoke = False
    try:
        async for sentence in groq_stream(history):
            spoke = True
            logger.info("llm: %r", sentence)
            yield sentence
    except Exception:
        logger.exception("llm: generation failed")
        # Only apologise if the caller has heard nothing yet; interrupting a
        # reply in progress with an apology is worse than ending it short.
        if not spoke:
            yield FALLBACK_REPLY


async def llm(history: list[dict[str, str]]) -> str:
    """Generate the whole reply to `history` as one string."""
    return " ".join([sentence async for sentence in llm_stream(history)])


async def tts_stream(text: str) -> AsyncIterator[bytes]:
    """Yield `text` as 8 kHz u-law audio, in chunks as it is synthesised."""
    if settings.VOICE_TTS_PROVIDER == "local":
        yield await local_tts(text)
        return

    from voice_service.providers.magpie_tts import tts_stream as magpie_stream

    produced = False
    try:
        async for chunk in magpie_stream(text):
            produced = True
            yield chunk
    except Exception:
        logger.exception("tts: Magpie failed")
        # Restarting locally after some audio has played would repeat part of
        # the sentence, so only fall back before the first chunk.
        if not produced:
            yield await local_tts(text)


async def tts(text: str) -> bytes:
    """Render a reply as 8 kHz u-law audio for the trunk."""
    return b"".join([chunk async for chunk in tts_stream(text)])
