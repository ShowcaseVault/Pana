"""Cache-layer tests.

L2 is stubbed with an in-process dict, so these run without a Redis server: what
is under test is the promotion and invalidation logic in `CacheService`, not the
Redis client itself.
"""

import pytest

from api.cache.service.cache import CacheService
from api.cache.service.in_memory_cache import InMemoryCacheService
from api.constants.cache_keys import RecordingCacheKeys, UserCacheKeys


class FakeRedisCache:
    """Stand-in for RedisCacheService that records how often it is touched."""

    def __init__(self) -> None:
        self.store: dict = {}
        self.get_calls = 0
        self.set_calls = 0

    async def get(self, key):
        self.get_calls += 1
        return self.store.get(key)

    async def set(self, key, value, ttl=None):
        self.set_calls += 1
        self.store[key] = value

    async def delete(self, key):
        self.store.pop(key, None)

    async def delete_pattern(self, pattern, batch_size=500):
        prefix = pattern.rstrip("*")
        matched = [k for k in self.store if k.startswith(prefix)]
        for key in matched:
            self.store.pop(key)
        return len(matched)


@pytest.fixture
def cache() -> CacheService:
    service = CacheService()
    service.l2 = FakeRedisCache()
    return service


def counting_fallback(value):
    """Return a fallback coroutine plus a list recording each invocation."""
    calls = []

    async def fallback():
        calls.append(1)
        return value

    return fallback, calls


class TestKeys:
    def test_keys_are_namespaced_and_stable(self):
        assert UserCacheKeys.profile(7) == "pana:users:7:profile"
        assert RecordingCacheKeys.detail(7, 42) == "pana:recordings:7:detail:42"

    def test_detail_and_listing_keys_share_the_group_prefix(self):
        prefix = RecordingCacheKeys.prefix(7)
        assert RecordingCacheKeys.detail(7, 42).startswith(prefix)
        assert RecordingCacheKeys.listing(7, 1, 20).startswith(prefix)

    def test_prefix_does_not_span_users(self):
        assert not RecordingCacheKeys.detail(8, 42).startswith(RecordingCacheKeys.prefix(7))


class TestReadThrough:
    async def test_miss_calls_fallback_and_fills_both_layers(self, cache):
        fallback, calls = counting_fallback({"id": 1})

        result = await cache.get("k", fallback)

        assert result == {"id": 1}
        assert len(calls) == 1
        assert await cache.l1.get("k") == {"id": 1}
        assert cache.l2.store["k"] == {"id": 1}

    async def test_l1_hit_does_not_touch_l2_or_fallback(self, cache):
        await cache.l1.set("k", {"id": 1})
        fallback, calls = counting_fallback({"id": 2})

        result = await cache.get("k", fallback)

        assert result == {"id": 1}
        assert calls == []
        assert cache.l2.get_calls == 0

    async def test_l2_hit_promotes_into_l1(self, cache):
        cache.l2.store["k"] = {"id": 1}
        fallback, calls = counting_fallback({"id": 2})

        assert await cache.get("k", fallback) == {"id": 1}
        assert calls == []
        assert await cache.l1.get("k") == {"id": 1}

    async def test_second_call_after_a_miss_is_served_from_l1(self, cache):
        fallback, calls = counting_fallback({"id": 1})

        await cache.get("k", fallback)
        await cache.get("k", fallback)

        assert len(calls) == 1

    async def test_empty_list_is_cached_and_not_treated_as_a_miss(self, cache):
        fallback, calls = counting_fallback([])

        await cache.get("k", fallback)
        await cache.get("k", fallback)

        assert len(calls) == 1


class TestShouldCache:
    async def test_rejected_value_is_returned_but_not_stored(self, cache):
        fallback, _ = counting_fallback([])

        result = await cache.get("k", fallback, should_cache=bool)

        assert result == []
        assert await cache.l1.get("k") is None
        assert cache.l2.set_calls == 0

    async def test_accepted_value_is_stored(self, cache):
        fallback, _ = counting_fallback([{"id": 1}])

        await cache.get("k", fallback, should_cache=bool)

        assert cache.l2.store["k"] == [{"id": 1}]


class TestTtl:
    async def test_callable_ttl_is_resolved_from_the_built_value(self, cache):
        seen = {}

        async def set_spy(key, value, ttl=None):
            seen["ttl"] = ttl
            cache.l2.store[key] = value

        cache.l2.set = set_spy
        fallback, _ = counting_fallback({"seconds": 120})

        await cache.get("k", fallback, ttl=lambda v: v["seconds"])

        assert seen["ttl"] == 120

    async def test_fixed_ttl_is_passed_through(self, cache):
        seen = {}

        async def set_spy(key, value, ttl=None):
            seen["ttl"] = ttl
            cache.l2.store[key] = value

        cache.l2.set = set_spy
        fallback, _ = counting_fallback({"id": 1})

        await cache.get("k", fallback, ttl=30)

        assert seen["ttl"] == 30


class TestInvalidation:
    async def test_invalidate_clears_both_layers(self, cache):
        fallback, calls = counting_fallback({"id": 1})
        await cache.get("k", fallback)

        await cache.invalidate("k")

        assert await cache.l1.get("k") is None
        assert "k" not in cache.l2.store
        await cache.get("k", fallback)
        assert len(calls) == 2

    async def test_invalidate_prefix_clears_the_group_only(self, cache):
        listing = RecordingCacheKeys.listing(7, 1, 20)
        detail = RecordingCacheKeys.detail(7, 42)
        other_user = RecordingCacheKeys.detail(8, 42)
        for key in (listing, detail, other_user):
            await cache.get(key, counting_fallback({"k": key})[0])

        await cache.invalidate_prefix(RecordingCacheKeys.prefix(7))

        assert await cache.l1.get(listing) is None
        assert await cache.l1.get(detail) is None
        assert await cache.l1.get(other_user) is not None
        assert other_user in cache.l2.store

    async def test_set_writes_both_layers_without_a_fallback(self, cache):
        await cache.set("k", {"id": 1})

        assert await cache.l1.get("k") == {"id": 1}
        assert cache.l2.store["k"] == {"id": 1}


class TestInMemoryLayer:
    async def test_eviction_respects_maxsize(self):
        l1 = InMemoryCacheService(maxsize=2, ttl=60)
        await l1.set("a", {"v": 1})
        await l1.set("b", {"v": 2})
        await l1.set("c", {"v": 3})

        assert len(l1.keys()) == 2

    async def test_delete_prefix_returns_the_number_removed(self):
        l1 = InMemoryCacheService(maxsize=10, ttl=60)
        await l1.set("pana:a:1", {"v": 1})
        await l1.set("pana:a:2", {"v": 2})
        await l1.set("pana:b:1", {"v": 3})

        assert await l1.delete_prefix("pana:a") == 2
        assert l1.keys() == ["pana:b:1"]
