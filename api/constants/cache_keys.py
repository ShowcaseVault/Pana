"""Cache key builders.

Every key the cache layer stores is built here, never inline at the call site, so
the shape of a key and the prefix used to invalidate a group of keys stay in one
place. Keys are colon-separated and namespaced by `CACHE_KEY_PREFIX`:

    pana:<domain>:<scope>:<identifier>

Each class pairs the concrete key builders with the prefix that covers them, so
a write can invalidate one entry or the whole group.
"""

from api.config.config import settings

PREFIX = settings.CACHE_KEY_PREFIX


class UserCacheKeys:
    @staticmethod
    def prefix(user_id: int) -> str:
        return f"{PREFIX}:users:{user_id}"

    @staticmethod
    def profile(user_id: int) -> str:
        return f"{PREFIX}:users:{user_id}:profile"

    @staticmethod
    def by_sub(sub: str) -> str:
        return f"{PREFIX}:users:sub:{sub}"


class RecordingCacheKeys:
    @staticmethod
    def prefix(user_id: int) -> str:
        return f"{PREFIX}:recordings:{user_id}"

    @staticmethod
    def detail(user_id: int, recording_id: int) -> str:
        return f"{PREFIX}:recordings:{user_id}:detail:{recording_id}"

    @staticmethod
    def listing(user_id: int, page: int, page_size: int) -> str:
        return f"{PREFIX}:recordings:{user_id}:list:{page}:{page_size}"


class TranscriptionCacheKeys:
    @staticmethod
    def prefix(user_id: int) -> str:
        return f"{PREFIX}:transcriptions:{user_id}"

    @staticmethod
    def detail(user_id: int, transcription_id: int) -> str:
        return f"{PREFIX}:transcriptions:{user_id}:detail:{transcription_id}"

    @staticmethod
    def by_recording(user_id: int, recording_id: int) -> str:
        return f"{PREFIX}:transcriptions:{user_id}:recording:{recording_id}"


class DiaryCacheKeys:
    @staticmethod
    def prefix(user_id: int) -> str:
        return f"{PREFIX}:diaries:{user_id}"

    @staticmethod
    def by_date(user_id: int, date: str) -> str:
        """`date` is an ISO date string (YYYY-MM-DD)."""
        return f"{PREFIX}:diaries:{user_id}:date:{date}"

    @staticmethod
    def listing(user_id: int, page: int, page_size: int) -> str:
        return f"{PREFIX}:diaries:{user_id}:list:{page}:{page_size}"


class HistoryCacheKeys:
    @staticmethod
    def prefix(user_id: int) -> str:
        return f"{PREFIX}:history:{user_id}"

    @staticmethod
    def by_date(user_id: int, date: str) -> str:
        return f"{PREFIX}:history:{user_id}:date:{date}"
