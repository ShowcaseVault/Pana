"""Process-local L1 cache.

One instance per worker process, so entries are not shared between the API and
Celery workers. Short TTLs only; L2 is the cross-process layer.
"""

import asyncio
import logging
from typing import Any

from cachetools import TTLCache

logger = logging.getLogger(__name__)


class InMemoryCacheService:
    def __init__(self, maxsize: int = 500, ttl: int = 60) -> None:
        self._cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        return self._cache.get(key)

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            self._cache[key] = value

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._cache.pop(key, None)
            logger.debug("L1 invalidated: %s", key)

    async def delete_prefix(self, prefix: str) -> int:
        async with self._lock:
            matched = [k for k in self._cache if k.startswith(prefix)]
            for key in matched:
                self._cache.pop(key, None)
            logger.debug("L1 prefix invalidated: %s (%d keys)", prefix, len(matched))
            return len(matched)

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()

    def keys(self) -> list[str]:
        return list(self._cache.keys())

    def entries(self) -> dict:
        return dict(self._cache)

    @property
    def stats(self) -> dict:
        return {
            "size": len(self._cache),
            "maxsize": self._cache.maxsize,
            "currsize": self._cache.currsize,
        }
