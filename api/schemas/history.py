from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from pydantic.config import ConfigDict

class HistoryCalendar(BaseModel):
    year : int
    month : int
    days_in_month : int
    diary_days : List[int] = []
    recording_days : List[int] = []

class HistoryFetch(BaseModel):
    history_date: Optional[date] = None