"""Redis connection used by the cache layer.

Separate from `pubsub_connection`, which serves pub/sub: that one returns
bytes, this one decodes to `str` because cached values are JSON. It also points
at its own Redis database, so a pattern delete from the cache never walks the
pub/sub keyspace.

`setup_redis_client()` runs from the application lifespan; `get_cache_redis()`
falls back to creating the client on first use, so Celery workers and scripts
that never run the lifespan still work.
"""

import logging

import redis.asyncio as aioredis

from api.config.config import settings

logger = logging.getLogger("redis")

# Global, mirroring how the database engine is held in database_connection.
redis_client: aioredis.Redis | None = None


def _create_client() -> aioredis.Redis:
    return aioredis.from_url(
        settings.REDIS_CACHE_URL,
        decode_responses=True,
        health_check_interval=30,
    )


async def setup_redis_client() -> aioredis.Redis:
    """Create the cache client and verify the connection.

    A failed ping is logged and swallowed: the cache is not allowed to block
    startup, and `RedisCacheService` already degrades every miss safely.
    """
    global redis_client
    if redis_client is None:
        redis_client = _create_client()
    try:
        await redis_client.ping()
        logger.debug("Connected to cache Redis successfully")
    except Exception as e:
        logger.error(f"Failed to connect to cache Redis: {e}")
    return redis_client


def get_cache_redis() -> aioredis.Redis:
    """Return the shared cache client, creating it if the lifespan has not run."""
    global redis_client
    if redis_client is None:
        redis_client = _create_client()
        logger.debug("Cache Redis client created on first use")
    return redis_client


async def redis_disconnect() -> None:
    """Close the shared client. Called from the application lifespan."""
    global redis_client
    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None
        logger.debug("Cache Redis client closed")
