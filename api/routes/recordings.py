from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import get_authorized_db_user
from api.connections import get_async_db_session
from api.cruds.recordings import (
    create_recording,
    delete_recording,
    get_all_recordings,
    get_recording_by_id,
    update_recording,
)
from api.cruds.transcriptions import create_transcription
from api.exceptions import BadRequestError, NotFoundError, error_docs
from api.schemas.recordings import RecordingCreate, RecordingResponse, RecordingUpdate
from api.schemas.response import ApiResponse
from api.schemas.transcriptions import TranscriptionCreate
from celery_service.tasks.transcription import transcribe_audio_task

router = APIRouter(prefix="/recordings", tags=["Recordings"])


_ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".webm", ".flac"}


@router.post("", responses=error_docs(400, 401))
async def create_recording_endpoint(
    file: UploadFile = File(...),
    duration_seconds: int = Form(...),
    recorded_at: datetime = Form(...),
    location_text: str | None = Form(None),
    user=Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ApiResponse[RecordingResponse]:
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("audio/"):
        filename = (file.filename or "").lower()
        if not any(filename.endswith(ext) for ext in _ALLOWED_AUDIO_EXTENSIONS):
            raise BadRequestError("Uploaded file must be an audio file")

    payload = RecordingCreate(
        duration_seconds=duration_seconds,
        recorded_at=recorded_at,
        location_text=location_text,
    )

    # 1. Create recording
    new_recording = await create_recording(
        db=db, file=file, user_id=user.id, user_sub=user.google_id, recording_data=payload
    )

    # 2. Create transcription
    create_transcription_payload = TranscriptionCreate(recording_id=new_recording.id)
    transcription = await create_transcription(
        db=db,
        payload=create_transcription_payload,
        user_id=user.id,
    )

    # 3. enqueue celery task
    # Commit before dispatching: the worker runs in another process and would
    # not see rows still sitting in this request's open transaction.
    if transcription:
        await db.commit()
        transcribe_audio_task.apply_async(args=[transcription.id], queue="default")

    return ApiResponse(data=new_recording, message="Recording created successfully")


@router.get("", responses=error_docs(401))
async def get_recordings_endpoint(
    skip: int = 0,
    limit: int = 100,
    recording_date: date | None = None,
    list_all: bool | None = False,
    user=Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ApiResponse[list[RecordingResponse]]:
    recordings = await get_all_recordings(db, user.id, skip, limit, recording_date, list_all)
    return ApiResponse(data=recordings, message="Recordings retrieved successfully")


@router.get("/{recording_id}", responses=error_docs(401, 404))
async def get_recording_endpoint(
    recording_id: int,
    user=Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ApiResponse[RecordingResponse]:
    recording = await get_recording_by_id(db, recording_id, user.id)
    if not recording:
        raise NotFoundError("Recording not found")

    return ApiResponse(
        data=RecordingResponse.model_validate(recording),
        message="Recording retrieved successfully",
    )


@router.patch("/{recording_id}", responses=error_docs(401, 404))
async def update_recording_endpoint(
    recording_id: int,
    update_data: RecordingUpdate,
    user=Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ApiResponse[RecordingResponse]:
    recording = await update_recording(db, recording_id, update_data, user.id)
    if not recording:
        raise NotFoundError("Recording not found")

    return ApiResponse(data=recording, message="Recording updated successfully")


@router.delete("/{recording_id}", responses=error_docs(401, 404))
async def delete_recording_endpoint(
    recording_id: int,
    user=Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ApiResponse[None]:
    deleted = await delete_recording(db, recording_id, user.id)
    if not deleted:
        raise NotFoundError("Recording not found")

    return ApiResponse(data=None, message="Recording deleted successfully")
