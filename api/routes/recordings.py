"""Recording endpoints."""

from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import get_authorized_db_user
from api.connections import get_async_db_session
from api.exceptions import error_docs
from api.models.users import User
from api.repositories import (
    RecordingFileRepository,
    RecordingRepository,
    TranscriptionRepository,
)
from api.schemas.recordings import (
    RecordingListResponse,
    RecordingResponse,
    RecordingUpdate,
)
from api.schemas.response import ApiResponse
from api.services.recordings import RecordingService
from celery_service.tasks.transcription import transcribe_audio_task

router = APIRouter(prefix="/recordings", tags=["Recordings"])


def get_recording_service(
    db: AsyncSession = Depends(get_async_db_session),
) -> RecordingService:
    """Build the recording service with the repositories it needs."""
    return RecordingService(
        recordings=RecordingRepository(db),
        transcriptions=TranscriptionRepository(db),
        files=RecordingFileRepository(),
    )


@router.post("", responses=error_docs(400, 401))
async def create_recording(
    file: UploadFile = File(...),
    duration_seconds: int = Form(...),
    recorded_at: datetime = Form(...),
    location_text: str | None = Form(None),
    user: User = Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session),
    service: RecordingService = Depends(get_recording_service),
) -> ApiResponse[RecordingResponse]:
    """Upload a recording and queue it for transcription."""
    recording, transcription_id = await service.create(
        file=file,
        user_id=user.id,
        user_sub=user.google_id,
        duration_seconds=duration_seconds,
        recorded_at=recorded_at,
        location_text=location_text,
    )

    if transcription_id is not None:
        # Commit before dispatching: the worker runs in another process and
        # would not see rows still sitting in this request's transaction.
        await db.commit()
        transcribe_audio_task.apply_async(args=[transcription_id], queue="default")

    return ApiResponse(data=recording, message="Recording created successfully")


@router.get("", responses=error_docs(401))
async def list_recordings(
    skip: int = 0,
    limit: int = 100,
    recording_date: date | None = None,
    list_all: bool = False,
    user: User = Depends(get_authorized_db_user),
    service: RecordingService = Depends(get_recording_service),
) -> ApiResponse[RecordingListResponse]:
    """List the user's recordings. Defaults to today unless `list_all` is set."""
    recordings, total = await service.list(
        user.id,
        skip=skip,
        limit=limit,
        recording_date=recording_date,
        list_all=list_all,
    )
    return ApiResponse(
        data=RecordingListResponse(total=total, data=recordings),
        message="Recordings retrieved successfully",
    )


@router.get("/{recording_id}", responses=error_docs(401, 404))
async def get_recording(
    recording_id: int,
    user: User = Depends(get_authorized_db_user),
    service: RecordingService = Depends(get_recording_service),
) -> ApiResponse[RecordingResponse]:
    """Return one recording."""
    recording = await service.get(recording_id, user.id)
    return ApiResponse(data=recording, message="Recording retrieved successfully")


@router.patch("/{recording_id}", responses=error_docs(401, 404))
async def update_recording(
    recording_id: int,
    changes: RecordingUpdate,
    user: User = Depends(get_authorized_db_user),
    service: RecordingService = Depends(get_recording_service),
) -> ApiResponse[RecordingResponse]:
    """Update a recording's metadata."""
    recording = await service.update(recording_id, user.id, changes)
    return ApiResponse(data=recording, message="Recording updated successfully")


@router.delete("/{recording_id}", responses=error_docs(401, 404))
async def delete_recording(
    recording_id: int,
    user: User = Depends(get_authorized_db_user),
    service: RecordingService = Depends(get_recording_service),
) -> ApiResponse[None]:
    """Soft-delete a recording and its transcription."""
    await service.delete(recording_id, user.id)
    return ApiResponse(data=None, message="Recording deleted successfully")
