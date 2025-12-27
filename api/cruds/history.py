import calendar
from datetime import date as _date
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.diary import Diary
from api.models.recordings import Recording
from api.schemas.history import HistoryCalendar
from api.schemas.recordings import RecordingResponse
from api.schemas.diary import DiaryResponse


async def fetch_calendar(
    db: AsyncSession,
    user_id: int,
    year: int,
    month: int
):
    today = _date.today()
    target_year = year or today.year
    target_month = month or today.month

    # Basic validation and normalization
    if target_month < 1 or target_month > 12:
        target_month = today.month
    if target_year < 1:
        target_year = today.year

    # Compute month range
    _, last_day = calendar.monthrange(target_year, target_month)
    start_date = _date(target_year, target_month, 1)
    end_date = _date(target_year, target_month, last_day)
    days_in_month = end_date - start_date

    # Fetch diary days within the month
    diary_stmt = select(Diary.diary_date).where(
        Diary.user_id == user_id,
        Diary.is_deleted == False,
        Diary.diary_date >= start_date,
        Diary.diary_date <= end_date,
    )
    diary_result = await db.execute(diary_stmt)
    diary_days = sorted({d.day for d in diary_result.scalars().all()})

    # Fetch recording days within the month
    rec_stmt = select(Recording.recording_date).where(
        Recording.user_id == user_id,
        Recording.is_deleted == False,
        Recording.recording_date >= start_date,
        Recording.recording_date <= end_date,
    )
    rec_result = await db.execute(rec_stmt)
    recording_days = sorted({r.day for r in rec_result.scalars().all()})

    return HistoryCalendar(
        year=target_year,
        month=target_month,
        days_in_month= days_in_month.days,
        diary_days=diary_days,
        recording_days=recording_days,
    )