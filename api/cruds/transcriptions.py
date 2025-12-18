from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.recordings import Recording
from api.models.transcriptions import Transcription
from api.schemas.transcriptions import (
    TranscriptionCreate,
    TranscriptionUpdate,
    TranscriptionResponse,
)


async def create_transcription(
    db: AsyncSession,
    payload: TranscriptionCreate,
    user_id: int,
):
    recording_result = await db.execute(
        select(Recording).where(
            Recording.id == payload.recording_id,
            Recording.user_id == user_id,
            Recording.is_deleted == False,
        )
    )
    recording = recording_result.scalars().first()
    if not recording:
        return None

    existing_result = await db.execute(
        select(Transcription).where(
            Transcription.recording_id == payload.recording_id,
            Transcription.is_deleted == False,
        )
    )
    existing = existing_result.scalars().first()
    if existing:
        return False

    new_transcription = Transcription(
        recording_id=payload.recording_id,
        model_name=payload.model_name,
        status=payload.status or "pending",
        is_deleted=False,
    )
    db.add(new_transcription)
    await db.commit()
    await db.refresh(new_transcription)
    return TranscriptionResponse.model_validate(new_transcription)


async def get_all_transcription(
    db: AsyncSession,
    skip: int,
    limit: int,
    user_id: int,
    status: Optional[str] = None,
):
    query_stmt = (
        select(Transcription)
        .join(Recording, Recording.id == Transcription.recording_id)
        .where(
            Transcription.is_deleted == False,
            Recording.user_id == user_id,
            Recording.is_deleted == False,
        )
        .order_by(Transcription.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if status:
        query_stmt = query_stmt.filter(Transcription.status == status)
    
    count_stmt = (
        select(func.count())
        .select_from(Transcription)
        .join(Recording, Recording.id == Transcription.recording_id)
        .where(
            Transcription.is_deleted == False,
            Recording.user_id == user_id,
            Recording.is_deleted == False,
        )
    )
    if status:
        count_stmt = count_stmt.filter(Transcription.status == status)

    result = await db.execute(query_stmt)
    count_result = await db.execute(count_stmt)
    transcriptions = result.scalars().all()
    total = count_result.scalar_one()

    return {
        "total": total,
        "data": [
            TranscriptionResponse.model_validate(t)
            for t in transcriptions
        ],
    }


async def get_transcription_by_id(
    db: AsyncSession,
    transcription_id: int,
    user_id: int,
):
    result = await db.execute(
        select(Transcription)
        .join(Recording, Recording.id == Transcription.recording_id)
        .where(
            Transcription.id == transcription_id,
            Transcription.is_deleted == False,
            Recording.user_id == user_id,
            Recording.is_deleted == False,
        )
    )
    return result.scalars().first()


async def update_transcription(
    db: AsyncSession,
    transcription_id: int,
    update_data: TranscriptionUpdate,
    user_id: int,
):
    transcription = await get_transcription_by_id(db, transcription_id, user_id)
    if not transcription:
        return None

    data = update_data.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(transcription, key, value)

    await db.commit()
    await db.refresh(transcription)
    return TranscriptionResponse.model_validate(transcription)


async def delete_transcription(
    db: AsyncSession,
    transcription_id: int,
    user_id: int,
) -> bool:
    transcription = await get_transcription_by_id(db, transcription_id, user_id)
    if not transcription:
        return False

    transcription.is_deleted = True
    await db.commit()
    return True