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
import queue
import threading
from collections.abc import AsyncIterator

from api.config.config import settings
from voice_service.audio import pcm_to_ulaw

logger = logging.getLogger("voice.magpie")

# Sentinel the producer thread puts on the queue when the stream is done, so
# the consumer stops on it rather than on a timeout.
_DONE = object()

# Chunks the producer may run ahead by. Bounded so synthesis cannot outrun
# playback and hold a whole reply in memory.
QUEUE_CHUNKS = 16
# How long a producer waits for room before checking whether it has been told
# to stop. Only reached when the consumer has stalled or gone.
OFFER_TIMEOUT = 0.5


def _offer(chunks: queue.Queue, item: object, stop: threading.Event) -> None:
    """Put `item` on the queue, giving up if the consumer has gone away.

    A plain blocking put deadlocks a consumer that stopped iterating: the
    thread parks on a full queue that nobody will drain again. The timeout is
    what lets the thread notice `stop` and unwind instead.
    """
    while not stop.is_set():
        try:
            chunks.put(item, timeout=OFFER_TIMEOUT)
            return
        except queue.Full:
            continue


def loop_run(fn):
    """Run `fn` on the default executor, as a future the caller can await."""
    return asyncio.get_running_loop().run_in_executor(None, fn)


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

    # A thread-native queue, not an asyncio one: the producer must be able to
    # make progress, and to notice it has been told to stop, without the event
    # loop scheduling anything on its behalf. Bounded so a fast synthesiser
    # cannot outrun playback and hold the whole reply in memory.
    chunks: queue.Queue = queue.Queue(maxsize=QUEUE_CHUNKS)
    # Set when the consumer goes away -- a caller that stops iterating because
    # the caller hung up, which is the common case, not an edge one.
    stop = threading.Event()

    def produce() -> None:
        try:
            for response in _get_service().synthesize_online(**_request(text)):
                if stop.is_set():
                    # Abandoning the gRPC iterator closes the stream, so the
                    # rest of the reply is never synthesised or billed.
                    break
                if response.audio:
                    _offer(chunks, response.audio, stop)
        except Exception as error:  # surfaced to the consumer, not swallowed
            _offer(chunks, error, stop)
        finally:
            _offer(chunks, _DONE, stop)

    task = loop_run(produce)
    # Resampling carries state between chunks. Without it each chunk is
    # resampled from a standing start and the fractional sample at its edge is
    # lost -- 22.05 kHz to 8 kHz is a ratio of 2.75625, so every boundary is
    # mid-sample and every boundary clicks.
    resample_state = None
    try:
        while True:
            item = await asyncio.to_thread(chunks.get)
            if item is _DONE:
                break
            if isinstance(item, Exception):
                raise item
            audio, resample_state = pcm_to_ulaw(item, settings.TTS_SAMPLE_RATE, resample_state)
            yield audio
    finally:
        # Tell the producer to stop and drain whatever it already queued, so a
        # thread parked on a full queue can always finish. Without this an
        # abandoned generator leaks a thread from the executor pool for good.
        stop.set()
        while True:
            try:
                chunks.get_nowait()
            except queue.Empty:
                break
        await task


async def tts(text: str) -> bytes:
    """Synthesise `text` and return all of it as 8 kHz u-law."""
    return b"".join([chunk async for chunk in tts_stream(text)])
