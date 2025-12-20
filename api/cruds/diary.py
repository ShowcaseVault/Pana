from datetime import date as _date
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from api.models.diary import Diary
from api.models.recordings import Recording
from api.models.transcriptions import Transcription
from api.schemas.diary import DiaryResponse
from api.services.diary import generate_diary_from_recordings


async def create_or_update_today_diary(
    db: AsyncSession,
    user_id: int,
) -> DiaryResponse:
    today = _date.today()

    # Fetch recordings for today with their transcriptions
    rec_stmt = (
        select(Recording)
        .where(
            Recording.user_id == user_id,
            Recording.is_deleted == False,
            Recording.recording_date == today,
        )
        .options(joinedload(Recording.transcription))
    )
    rec_result = await db.execute(rec_stmt)
    recordings: List[Recording] = rec_result.scalars().all()

    # Use service to generate mood/content/actions
    summary = generate_diary_from_recordings(recordings)

    # Upsert diary (unique user_id on Diary implies single row per user)
    diary_result = await db.execute(
        select(Diary).where(Diary.user_id == user_id)
    )
    diary: Optional[Diary] = diary_result.scalars().first()

    if diary:
        diary.diary_date = today
        diary.mood = summary.get("mood")
        diary.content = summary.get("content")
        diary.actions = summary.get("actions")
        diary.is_deleted = False
    else:
        diary = Diary(
            user_id=user_id,
            diary_date=today,
            mood=summary.get("mood"),
            content=summary.get("content"),
            actions=summary.get("actions"),
            is_deleted=False,
        )
        db.add(diary)

    await db.commit()
    await db.refresh(diary)

    return DiaryResponse.model_validate(diary)
