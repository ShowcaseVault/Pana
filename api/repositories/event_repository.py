"""Redis pub/sub for transcription events.

Both ends of the channel live here so they cannot drift: the Celery worker
publishes through `publish_transcription_completed`, the SSE route subscribes
through `TranscriptionEventRepository`, and neither spells the channel name out
for itself.
"""

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import redis.asyncio as aioredis

from api.connections import get_async_redis_client, get_redis_client

logger = logging.getLogger("pubsub")


def channel_for(user_id: int) -> str:
    """Return the transcription-event channel belonging to one user.

    Events are per-user channels rather than one broadcast channel: a shared
    channel would deliver every user's activity to every listener, and the
    subscriber would have to be trusted to discard what is not theirs.
    """
    return f"transcription_completed:{user_id}"


def publish_transcription_completed(
    user_id: int, *, transcription_id: int, recording_id: int, status: str
) -> None:
    """Announce that a transcription finished. Called from the Celery worker.

    Synchronous because the worker is; failures are logged and swallowed, since
    a missed notification must not fail a transcription that already succeeded.
    """
    payload = {
        "transcription_id": transcription_id,
        "recording_id": recording_id,
        "status": status,
    }

    try:
        get_redis_client().publish(channel_for(user_id), json.dumps(payload))
    except Exception:
        logger.exception("Could not publish transcription %s", transcription_id)


class TranscriptionEventRepository:
    """Subscribes to one user's transcription events.

    Each instance owns its own Redis connection: a connection running
    `listen()` is dedicated to that subscription for its lifetime and cannot be
    shared with another subscriber.
    """

    def __init__(self, client: aioredis.Redis | None = None) -> None:
        self.client = client or get_async_redis_client()

    async def listen(self, user_id: int) -> AsyncIterator[dict[str, Any]]:
        """Yield each event published for this user until the caller stops.

        The connection is closed on the way out however the iteration ends --
        client disconnect, cancellation, or error -- because a subscriber that
        leaks its connection holds one open per dropped browser tab.
        """
        pubsub = self.client.pubsub()
        await pubsub.subscribe(channel_for(user_id))

        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue

                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")

                try:
                    yield json.loads(data)
                except json.JSONDecodeError:
                    logger.warning("Discarded malformed transcription event")
        finally:
            await pubsub.close()
            await self.client.aclose()
