from datetime import date as _date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from api.models.diary import Diary
from api.models.recordings import Recording
from api.models.transcriptions import Transcription
from api.schemas.diary import DiaryResponse
from api.services.diary import generate_diary_from_recordings


async def create_or_update_diary(
    db: AsyncSession,
    user_id: int,
    date: _date | None = None,
) -> DiaryResponse:
    target_date = date or _date.today()

    rec_stmt = (
        select(Recording)
        .where(
            Recording.user_id == user_id,
            Recording.deleted_at.is_(None),
            Recording.recording_date == target_date,
        )
        .options(joinedload(Recording.transcription))
    )
    rec_result = await db.execute(rec_stmt)
    recordings: list[Recording] = rec_result.scalars().all()

    tra_stmt = (
        select(Transcription)
        .join(Recording, Recording.id == Transcription.recording_id)
        .where(
            Recording.user_id == user_id,
            Transcription.deleted_at.is_(None),
            Transcription.transcribed_at == target_date,
        )
    )

    tra_result = await db.execute(tra_stmt)
    transcriptions: list[Transcription] = tra_result.scalars().all()

    # Diary Creating Service
    summary = await generate_diary_from_recordings(db, user_id, recordings, transcriptions)

    diary_result = await db.execute(
        select(Diary).where(
            Diary.user_id == user_id, Diary.diary_date == target_date, Diary.deleted_at.is_(None)
        )
    )
    diary: Diary | None = diary_result.scalars().first()

    if diary:
        diary.diary_date = target_date
        diary.mood = summary.get("mood")
        diary.content = summary.get("content")
        diary.actions = summary.get("actions")
        diary.recording_file_paths = [r.file_path for r in recordings]
        diary.deleted_at = None
    else:
        diary = Diary(
            user_id=user_id,
            diary_date=target_date,
            mood=summary.get("mood"),
            content=summary.get("content"),
            actions=summary.get("actions"),
            recording_file_paths=[r.file_path for r in recordings],
        )
        db.add(diary)

    await db.flush()
    await db.refresh(diary)

    return DiaryResponse.model_validate(diary)


async def get_diary(
    db: AsyncSession,
    user_id: int,
    date: _date | None = None,
) -> DiaryResponse:
    target_date = date or _date.today()

    stmt = select(Diary).where(
        Diary.user_id == user_id, Diary.diary_date == target_date, Diary.deleted_at.is_(None)
    )

    result = await db.execute(stmt)
    diary: Diary | None = result.scalars().first()

    if not diary:
        stmt_recording = select(Recording.file_path).where(
            Recording.user_id == user_id,
            Recording.recording_date == target_date,
            Recording.deleted_at.is_(None),
        )

        rec_result = await db.execute(stmt_recording)
        recordings: list[str] = rec_result.scalars().all()

        return DiaryResponse(
            diary_date=target_date,
            mood=None,
            content=None,
            actions=None,
            recording_file_paths=recordings,
        )

    return DiaryResponse.model_validate(diary)
