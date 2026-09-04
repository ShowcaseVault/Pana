"""Redis pub/sub connections.

Kept apart from `redis_connection`, which serves the cache: this one carries raw
bytes on its own Redis database, so a cache pattern delete never walks the
pub/sub keyspace.

Two clients, because the two ends differ. Celery publishes from synchronous task
code; the SSE route subscribes from async code. Publishers share one pooled
client, while each subscriber gets its own: a connection running `pubsub.listen()`
is dedicated to that subscription for its lifetime and cannot be shared.
"""

import logging

import redis
import redis.asyncio as aioredis

from api.config.config import settings

logger = logging.getLogger("pubsub")

# Shared publisher client (sync, used by Celery tasks).
publisher_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """Return the shared sync client used to publish events.

    Raises on connection failure rather than returning None, so a publish never
    fails later with an AttributeError far from the real cause.
    """
    global publisher_client
    if publisher_client is None:
        publisher_client = redis.Redis.from_url(settings.REDIS_PUBSUB_URL)
        publisher_client.ping()
        logger.info("Connected to pub/sub Redis successfully")
    return publisher_client


def get_async_redis_client() -> aioredis.Redis:
    """Create a new async client for one subscriber.

    Not shared and not cached: the caller owns it and must close it when the
    subscription ends.
    """
    return aioredis.from_url(settings.REDIS_PUBSUB_URL, decode_responses=False)


def pubsub_disconnect() -> None:
    """Close the shared publisher client."""
    global publisher_client
    if publisher_client is not None:
        publisher_client.close()
        publisher_client = None
        logger.info("Pub/sub publisher client closed")
