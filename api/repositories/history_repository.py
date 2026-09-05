"""Database access for the history calendar."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.diary import Diary
from api.models.recordings import Recording


class HistoryRepository:
    """Reads which days a user has activity on.

    Spans two tables because the calendar answers one question -- what did I do
    this month -- from both diaries and recordings.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def diary_days(self, user_id: int, start: date, end: date) -> list[int]:
        """Day-of-month numbers the user wrote a diary on, ascending."""
        stmt = select(Diary.diary_date).where(
            Diary.user_id == user_id,
            Diary.deleted_at.is_(None),
            Diary.diary_date >= start,
            Diary.diary_date <= end,
        )
        return await self._day_numbers(stmt)

    async def recording_days(self, user_id: int, start: date, end: date) -> list[int]:
        """Day-of-month numbers the user recorded on, ascending."""
        stmt = select(Recording.recording_date).where(
            Recording.user_id == user_id,
            Recording.deleted_at.is_(None),
            Recording.recording_date >= start,
            Recording.recording_date <= end,
        )
        return await self._day_numbers(stmt)

    async def _day_numbers(self, stmt) -> list[int]:
        """Collapse a column of dates into sorted, unique day-of-month numbers.

        Several rows on one day are one marked day on a calendar, so duplicates
        are dropped here rather than by the caller.
        """
        result = await self.db.execute(stmt)
        return sorted({value.day for value in result.scalars().all()})
