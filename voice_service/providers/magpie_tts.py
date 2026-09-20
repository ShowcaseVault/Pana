"""NVIDIA Magpie speech synthesis for the voice pipeline.

Magpie streams: it returns audio in chunks as it synthesises, rather than one
buffer at the end. `tts_stream` passes that through so the first chunk can go
to the trunk while the rest is still being made, which is most of the
difference between a reply that starts in a second and one that starts in
four.

Two deployments, one client. The hosted build runs on NVIDIA Cloud Functions,
which wants the function ID in the call metadata over TLS; a self-hosted NIM
(docker-compose.magpie.yml) is a plain gRPC target with neither. TTS_URI
picks between them -- see api/config/config.py.

riva-client is synchronous gRPC, so the stream is consumed on a worker thread
and handed back over a queue. Iterating it on the event loop directly would
block every other call on the service for the length of the synthesis.
"""

import asyncio
import logging
from collections.abc import AsyncIterator

from api.config.config import settings
from voice_service.audio import pcm_to_ulaw

logger = logging.getLogger("voice.magpie")

# Sentinel the producer thread puts on the queue when the stream is done, so
# the consumer stops on it rather than on a timeout.
_DONE = object()

_service = None


def _get_service():
    """Build the synthesis client once and reuse it.

    The channel does a TLS handshake on creation, so a client per turn would
    add that to every reply.
    """
    global _service
    if _service is not None:
        return _service

    import riva.client

    metadata = []
    if settings.TTS_FUNCTION_ID:
        if not settings.NVIDIA_API_KEY:
            raise RuntimeError(
                "NVIDIA_API_KEY is not set, which the hosted Magpie endpoint requires. "
                "Set it in .env, or point TTS_URI at a self-hosted NIM and clear "
                "TTS_FUNCTION_ID."
            )
        metadata = [
            ["function-id", settings.TTS_FUNCTION_ID],
            ["authorization", f"Bearer {settings.NVIDIA_API_KEY}"],
        ]

    auth = riva.client.Auth(
        uri=settings.TTS_URI,
        use_ssl=settings.TTS_USE_SSL,
        metadata_args=metadata,
    )
    logger.info("connecting to Magpie at %s", settings.TTS_URI)
    _service = riva.client.SpeechSynthesisService(auth)
    return _service


def _request(text: str) -> dict:
    import riva.client

    return {
        "text": text,
        "voice_name": settings.TTS_VOICE,
        "language_code": settings.TTS_LANGUAGE,
        "sample_rate_hz": settings.TTS_SAMPLE_RATE,
        "encoding": riva.client.AudioEncoding.LINEAR_PCM,
    }


async def tts_stream(text: str) -> AsyncIterator[bytes]:
    """Yield the spoken form of `text` as 8 kHz u-law, chunk by chunk."""
    if not text.strip():
        return

    loop = asyncio.get_running_loop()
    # Bounded so a fast synthesiser cannot outrun playback and hold the whole
    # reply in memory; the producer thread blocks instead.
    queue: asyncio.Queue = asyncio.Queue(maxsize=16)

    def produce() -> None:
        try:
            for response in _get_service().synthesize_online(**_request(text)):
                if response.audio:
                    # put_nowait would drop audio once the queue is full, and
                    # the thread is not the loop's, so hand it over properly.
                    asyncio.run_coroutine_threadsafe(queue.put(response.audio), loop).result()
        except Exception as error:  # surfaced to the consumer, not swallowed here
            asyncio.run_coroutine_threadsafe(queue.put(error), loop).result()
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(_DONE), loop).result()

    task = loop.run_in_executor(None, produce)
    try:
        while True:
            item = await queue.get()
            if item is _DONE:
                break
            if isinstance(item, Exception):
                raise item
            # Each chunk is whole samples at Magpie's rate, so it converts on
            # its own without carrying a remainder between chunks.
            yield pcm_to_ulaw(item, settings.TTS_SAMPLE_RATE)
    finally:
        await task


async def tts(text: str) -> bytes:
    """Synthesise `text` and return all of it as 8 kHz u-law."""
    return b"".join([chunk async for chunk in tts_stream(text)])
