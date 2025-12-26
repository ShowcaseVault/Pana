import os
import shutil
from pathlib import Path
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import joinedload
from datetime import date

from api.models.recordings import Recording
from api.models.transcriptions import Transcription
from api.cruds.transcriptions import get_transcription_by_id
from api.schemas.recordings import RecordingCreate, RecordingUpdate, RecordingResponse

from api.config.config import settings

async def create_recording(
    db: AsyncSession, 
    file: UploadFile, 
    user_id: int, 
    user_sub: str,
    recording_data: RecordingCreate
):
    """
    Create a new recording entry in the database and save the file.
    """
    duration_seconds = recording_data.duration_seconds
    recorded_at = recording_data.recorded_at
    location_text = recording_data.location_text
    
    recording_date = recorded_at.date()

    date_str = recorded_at.strftime("%Y-%m-%d")
    time_str = recorded_at.strftime("%H-%M-%S")
    
    file_extension = Path(file.filename).suffix
    if not file_extension:
        file_extension = ".wav" 
    
    filename = f"{time_str}{file_extension}"
    relative_path = Path(user_sub) / date_str / filename
    full_path = Path(settings.UPLOAD_DIR) / relative_path
    
    # Ensure dir exists
    os.makedirs(full_path.parent, exist_ok=True)
    
    # Save file
    try:
        with open(full_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")

    file_path_str = str(relative_path).replace("\\", "/")

    new_recording = Recording(
        user_id=user_id,
        file_path=file_path_str,
        duration_seconds=duration_seconds,
        recorded_at=recorded_at,
        recording_date=recording_date,
        location_text=location_text,
    )
    db.add(new_recording)
    await db.commit()
    await db.refresh(new_recording)
    return RecordingResponse.model_validate(new_recording)


async def get_recording_by_id(db: AsyncSession, recording_id: int, user_id: int):
    """
    Get a specific recording by ID for a specific user.
    """
    result = await db.execute(
        select(Recording).where(
            Recording.id == recording_id, 
            Recording.user_id == user_id,
            Recording.is_deleted == False
        ).options(joinedload(Recording.transcription))
    )
    recording = result.scalars().first()
    return recording


async def get_all_recordings(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    recording_date = None,
    list_all = False,
):
    if not list_all and recording_date is None:
        recording_date = date.today()

    query_stmt = select(Recording)
    count_stmt = select(func.count()).select_from(Recording)
    
    def apply_filters(stmt):
        conditions = [
            Recording.user_id == user_id,
            Recording.is_deleted == False,
        ]
        if not list_all:
            conditions.append(
                func.date(Recording.recorded_at) == recording_date
            )
        stmt = stmt.where(*conditions)
        return stmt


    query = (
        apply_filters(query_stmt)
        .order_by(desc(Recording.recorded_at))
        .options(joinedload(Recording.transcription))
        .offset(skip)
        .limit(limit)
    )
    
    count_query = apply_filters(count_stmt)

    result = await db.execute(query)
    count_result = await db.execute(count_query)
    recordings = result.scalars().all()
    total = count_result.scalar_one()

    return {
        "total" : total,
        "data" : [
            RecordingResponse.model_validate(recording)
            for recording in recordings
        ]
    }

async def update_recording(
    db: AsyncSession, recording_id: int, recording_update: RecordingUpdate, user_id: int
):
    """
    Update a recording's metadata.
    """
    recording = await get_recording_by_id(db, recording_id, user_id)
    if not recording:
        return None

    update_data = recording_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(recording, key, value)
        
    # If recorded_at is updated, update recording_date too
    if "recorded_at" in update_data:
        recording.recording_date = update_data["recorded_at"].date()

    await db.commit()
    await db.refresh(recording)
    return RecordingResponse.model_validate(recording)


async def delete_recording(db: AsyncSession, recording_id: int, user_id: int) -> bool:
    """
    Soft delete a recording.
    """
    recording = await get_recording_by_id(db, recording_id, user_id)
    transcription = await get_transcription_by_id(db, recording.transcription_id)
    if not recording or not transcription:
        return False
    
    recording.is_deleted = True
    transcription.is_deleted = True
    await db.commit()
    await db.refresh(recording)
    await db.refresh(transcription)
    return True
