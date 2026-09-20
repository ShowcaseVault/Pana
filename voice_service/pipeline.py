"""The voice pipeline: speech in, speech out.

Three stages, each behind one function, each hosted:

    stt   Groq, Whisper turbo
    llm   Groq, chat
    tts   NVIDIA Magpie

There is no offline path. Vosk and Piper were here while the providers were
undecided; they cost ~200 MB of models and packages to stand in for services
that are now configured, and a local recogniser that mishears the caller is not
a better call than a short apology. A stage that fails says so and the turn
ends -- the loop continues, so one bad turn does not end the call.

Two of the stages stream. `llm_stream` yields the reply a sentence at a time
and `tts_stream` yields audio as it is synthesised, which is what lets the
caller hear the first sentence while the rest is still being written. The
non-streaming forms remain for anything that wants the whole result.

Audio is 8 kHz mono u-law at every seam, which is what the trunk carries -- see
voice_service/audio.py for the conversions each model needs.
"""

import logging
from collections.abc import AsyncIterator

from voice_service.providers.groq_llm import llm_stream as groq_llm_stream
from voice_service.providers.groq_speech import stt as groq_stt
from voice_service.providers.magpie_tts import tts_stream as magpie_tts_stream

logger = logging.getLogger("voice.pipeline")

# Said when the caller's speech came through as nothing -- silence, or noise
# the recogniser could not resolve into words. A friend says this plainly and
# once; an assistant stacks apologies.
NO_SPEECH_REPLY = "Sorry, I missed that. Say it again?"

# Said when generation itself failed. The caller hears a sentence rather than
# silence, and the turn loop keeps going.
FALLBACK_REPLY = "Sorry, I lost my train of thought there. What were you saying?"


async def stt(audio: bytes) -> str:
    """Transcribe one turn of caller audio. Empty if recognition failed."""
    try:
        return await groq_stt(audio)
    except Exception:
        # Treated as a turn that came through as nothing, which the loop
        # already knows how to handle: re-prompt rather than drop the call.
        logger.exception("stt: transcription failed")
        return ""


async def llm_stream(history: list[dict[str, str]]) -> AsyncIterator[str]:
    """Yield the reply to `history` sentence by sentence.

    `history` is the conversation in OpenAI message shape, oldest first, ending
    with the caller's latest turn.
    """
    if not history or not history[-1].get("content", "").strip():
        yield NO_SPEECH_REPLY
        return

    spoke = False
    try:
        async for sentence in groq_llm_stream(history):
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
    try:
        async for chunk in magpie_tts_stream(text):
            yield chunk
    except Exception:
        # Nothing to fall back to: the caller hears the reply cut short, which
        # the next turn recovers from. Better than a dropped call.
        logger.exception("tts: synthesis failed")


async def tts(text: str) -> bytes:
    """Render a reply as 8 kHz u-law audio for the trunk."""
    return b"".join([chunk async for chunk in tts_stream(text)])
