from datetime import date

from pydantic import BaseModel


class HistoryCalendar(BaseModel):
    """Which days of a month hold something."""

    diary_days: list[int] = []
    recording_days: list[int] = []


class HistoryFetch(BaseModel):
    history_date: date | None = None
