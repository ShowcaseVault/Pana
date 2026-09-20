"""Groq-hosted text generation for the voice pipeline.

Exposes the reply two ways. `llm` returns the whole thing, which is what a
caller wants when the reply is going somewhere other than the trunk.
`llm_stream` yields it a sentence at a time, which is what makes chunked
playback possible: the first sentence can be synthesised and played while the
model is still writing the second, so the caller hears a reply in roughly the
time the first sentence takes rather than the whole turn.

Sentences, not tokens, are the unit because a synthesiser needs a complete
clause to get the prosody right -- handing Magpie three words at a time makes
speech that sounds chopped even though the audio is continuous.
"""

import logging
import re
from collections.abc import AsyncIterator

from api.config.config import settings
from api.connections import get_groq_client

logger = logging.getLogger("voice.groq")

# A sentence ends at .?! followed by whitespace. The lookbehind keeps the
# punctuation with the sentence it ends, so the synthesiser sees the cue that
# tells it to fall in pitch rather than hang.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

# Below this a "sentence" is an abbreviation or a stray fragment; flushing it
# on its own would synthesise a word by itself, which sounds like a stutter.
MIN_CHUNK_CHARS = 24


async def _completion(history: list[dict[str, str]], stream: bool):
    return await get_groq_client().chat.completions.create(
        model=settings.LLM_MODEL_REALTIME,
        messages=[{"role": "system", "content": settings.VOICE_LLM_PROMPT}, *history],
        max_completion_tokens=settings.LLM_MAX_TOKENS,
        temperature=settings.LLM_TEMPERATURE,
        stream=stream,
    )


async def llm_stream(history: list[dict[str, str]]) -> AsyncIterator[str]:
    """Yield the reply sentence by sentence as the model writes it.

    `history` is the conversation so far in OpenAI message shape, oldest first,
    ending with the caller's latest turn.
    """
    buffer = ""
    # A sentence too short to speak on its own waits here for the next one.
    pending = ""
    async for chunk in await _completion(history, stream=True):
        delta = chunk.choices[0].delta.content
        if not delta:
            continue
        buffer += delta
        # A sentence may complete mid-chunk, so split on every arrival and keep
        # the trailing fragment: it is the start of the next sentence, not a
        # finished one. Splitting the buffer rather than the delta is what lets
        # a sentence end land in the middle of a chunk.
        *finished, buffer = _SENTENCE_END.split(buffer)
        for sentence in finished:
            pending = f"{pending} {sentence}".strip()
            if len(pending) >= MIN_CHUNK_CHARS:
                yield pending
                pending = ""

    tail = f"{pending} {buffer}".strip()
    if tail:
        yield tail


async def llm(history: list[dict[str, str]]) -> str:
    """Generate the whole reply in one call."""
    response = await _completion(history, stream=False)
    text = (response.choices[0].message.content or "").strip()
    logger.info("llm: %r", text)
    return text
