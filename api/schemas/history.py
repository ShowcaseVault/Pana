from datetime import date

from pydantic import BaseModel


class HistoryCalendar(BaseModel):
    year: int
    month: int
    days_in_month: int
    diary_days: list[int] = []
    recording_days: list[int] = []


class HistoryFetch(BaseModel):
    history_date: date | None = None
