"""Two-layer read-through cache: process-local L1 in front of shared L2 (Redis).

Lookup order is L1, then L2, then the caller's `fallback`. A value produced by
the fallback is written back to both layers, so a later request on the same
worker is served from memory and a request on another worker from Redis.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from api.cache.service.in_memory_cache import InMemoryCacheService
from api.cache.service.redis_cache import RedisCacheService
from api.config.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=dict | list)

# Per-key L2 TTL: a fixed number of seconds, or a callable that derives it from
# the freshly built value (e.g. seconds until the value goes stale). None uses
# the service default.
TTLArg = int | Callable[[T], int | None] | None


class CacheService:
    def __init__(self) -> None:
        self.l1 = InMemoryCacheService(
            maxsize=settings.CACHE_L1_MAXSIZE,
            ttl=settings.CACHE_L1_TTL,
        )
        self.l2 = RedisCacheService(ttl=settings.CACHE_L2_TTL)

    async def get(
        self,
        key: str,
        fallback: Callable[[], Awaitable[T]],
        ttl: TTLArg = None,
        should_cache: Callable[[T], bool] | None = None,
    ) -> T:
        """Return the cached value for `key`, building it with `fallback` on a miss.

        `should_cache` vetoes writing a freshly built value (e.g. an empty result
        that should not be pinned for the full TTL).
        """
        if not settings.CACHE_ENABLED:
            return await fallback()

        value = await self.l1.get(key)
        if value is not None:
            return value

        value = await self.l2.get(key)
        if value is not None:
            await self.l1.set(key, value)
            return value

        logger.debug("Cache miss on both layers, calling fallback: %s", key)
        value = await fallback()

        if should_cache is None or should_cache(value):
            resolved_ttl = ttl(value) if callable(ttl) else ttl
            await self.l2.set(key, value, ttl=resolved_ttl)
            await self.l1.set(key, value)

        return value

    async def set(self, key: str, value: T, ttl: int | None = None) -> None:
        """Write a value into both layers without going through a fallback."""
        await self.l2.set(key, value, ttl=ttl)
        await self.l1.set(key, value)

    async def invalidate(self, key: str) -> None:
        await self.l1.delete(key)
        await self.l2.delete(key)
        # Fires on every write, so it is DEBUG: a person watching the terminal
        # wants to see the write, not the cache bookkeeping that follows it.
        logger.debug("Invalidated both layers: %s", key)

    async def invalidate_prefix(self, prefix: str) -> None:
        """Drop every key starting with `prefix` from both layers.

        L1 only clears in the calling process; other workers keep their copies
        until their own (short) TTL expires.
        """
        l1_count = await self.l1.delete_prefix(prefix)
        l2_count = await self.l2.delete_pattern(prefix)
        logger.debug(
            "Invalidated prefix on both layers: %s (l1=%d, l2=%d)", prefix, l1_count, l2_count
        )

    def keys(self) -> list[str]:
        return self.l1.keys()

    def entries(self) -> dict:
        return self.l1.entries()


cache_service = CacheService()
