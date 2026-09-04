"""Shared L2 cache backed by Redis.

Every Redis call is wrapped: a cache backend that is down must degrade to a miss,
never raise into the request path.
"""

import json
import logging
from typing import Any

from api.connections.redis_connection import get_cache_redis

logger = logging.getLogger(__name__)


class RedisCacheService:
    def __init__(self, ttl: int = 3600) -> None:
        self._ttl = ttl

    async def get(self, key: str) -> Any | None:
        try:
            value = await get_cache_redis().get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.warning("L2 get failed for key %s: %s", key, e)
        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        try:
            await get_cache_redis().setex(key, ttl or self._ttl, json.dumps(value, default=str))
        except Exception as e:
            logger.warning("L2 set failed for key %s: %s", key, e)

    async def delete(self, key: str) -> None:
        try:
            await get_cache_redis().delete(key)
        except Exception as e:
            logger.warning("L2 delete failed for key %s: %s", key, e)

    async def delete_pattern(self, pattern: str, batch_size: int = 500) -> int:
        """Delete every key matching a glob pattern, using non-blocking SCAN.

        A plain prefix is matched as `<prefix>*`. Returns the number of keys deleted.
        """
        deleted = 0
        match = pattern if "*" in pattern else f"{pattern}*"
        try:
            redis = get_cache_redis()
            batch: list[str] = []
            async for key in redis.scan_iter(match=match, count=batch_size):
                batch.append(key)
                if len(batch) >= batch_size:
                    deleted += await redis.delete(*batch)
                    batch = []
            if batch:
                deleted += await redis.delete(*batch)
        except Exception as e:
            logger.warning("L2 delete_pattern failed for %s: %s", match, e)
        return deleted
