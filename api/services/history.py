"""History calendar business logic."""

import calendar
from datetime import date

from api.repositories import HistoryRepository
from api.schemas.history import HistoryCalendar


class HistoryService:
    """Builds the month view of a user's activity."""

    def __init__(self, history: HistoryRepository) -> None:
        self.history = history

    async def calendar(
        self, user_id: int, year: int | None = None, month: int | None = None
    ) -> HistoryCalendar:
        """Return which days of a month the user has diaries or recordings on.

        An out-of-range or missing year or month falls back to today rather
        than failing: this backs a calendar widget, and a 422 on a stray month
        number would blank the screen over something the current month answers
        perfectly well.
        """
        target_year, target_month = self._resolve_month(year, month)

        days_in_month = calendar.monthrange(target_year, target_month)[1]
        start = date(target_year, target_month, 1)
        end = date(target_year, target_month, days_in_month)

        return HistoryCalendar(
            year=target_year,
            month=target_month,
            days_in_month=days_in_month,
            diary_days=await self.history.diary_days(user_id, start, end),
            recording_days=await self.history.recording_days(user_id, start, end),
        )

    @staticmethod
    def _resolve_month(year: int | None, month: int | None) -> tuple[int, int]:
        """Fall back to the current year or month for anything unusable."""
        today = date.today()
        target_year = year if year and year >= 1 else today.year
        target_month = month if month and 1 <= month <= 12 else today.month
        return target_year, target_month
