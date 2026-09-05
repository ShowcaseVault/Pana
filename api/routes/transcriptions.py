"""Transcription endpoints.

Only the two read endpoints are mounted. Creating, updating, and deleting a
transcription are the transcription worker's job, not a client's, so those
routes stay defined but unregistered -- see the note above each one.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import get_authorized_db_user
from api.connections import get_async_db_session
from api.exceptions import error_docs
from api.models.users import User
from api.repositories import RecordingRepository, TranscriptionRepository
from api.schemas.response import (
    ApiResponse,
    PaginatedResponse,
    Pagination,
    paginated,
    success,
)
from api.schemas.transcriptions import (
    TranscriptionCreate,
    TranscriptionResponse,
    TranscriptionStatus,
    TranscriptionUpdate,
)
from api.services.transcriptions import TranscriptionService

router = APIRouter(prefix="/transcriptions", tags=["Transcriptions"])


def get_transcription_service(
    db: AsyncSession = Depends(get_async_db_session),
) -> TranscriptionService:
    """Build the transcription service with the repositories it needs."""
    return TranscriptionService(
        transcriptions=TranscriptionRepository(db),
        recordings=RecordingRepository(db),
    )


@router.get("", responses=error_docs(401))
async def list_transcriptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    status: TranscriptionStatus | None = None,
    user: User = Depends(get_authorized_db_user),
    service: TranscriptionService = Depends(get_transcription_service),
) -> PaginatedResponse[list[TranscriptionResponse]]:
    """List the user's transcriptions, newest first."""
    transcriptions, total = await service.list(
        user.id,
        page=page,
        page_size=page_size,
        status=status.value if status else None,
    )
    return paginated(
        data=transcriptions,
        message="Transcriptions retrieved successfully",
        pagination=Pagination.build(page=page, page_size=page_size, total=total),
    )


@router.get("/{transcription_id}", responses=error_docs(401, 404))
async def get_transcription(
    transcription_id: int,
    user: User = Depends(get_authorized_db_user),
    service: TranscriptionService = Depends(get_transcription_service),
) -> ApiResponse[TranscriptionResponse]:
    """Return one transcription."""
    transcription = await service.get(transcription_id, user.id)
    return success(data=transcription, message="Transcription retrieved successfully")


# ── Not mounted ──────────────────────────────────────────────────────────────
#
# Transcriptions are created by uploading a recording and written by the Celery
# worker. These stay here, converted and ready, because exposing them is a
# decision about the product rather than about this code: add the decorator to
# mount one.


async def create_transcription(
    payload: TranscriptionCreate,
    user: User = Depends(get_authorized_db_user),
    service: TranscriptionService = Depends(get_transcription_service),
) -> ApiResponse[TranscriptionResponse]:
    """Queue a transcription for a recording that has none."""
    transcription = await service.create(
        payload.recording_id, user.id, model_name=payload.model_name
    )
    return success(data=transcription, message="Transcription created successfully")


async def update_transcription(
    transcription_id: int,
    changes: TranscriptionUpdate,
    user: User = Depends(get_authorized_db_user),
    service: TranscriptionService = Depends(get_transcription_service),
) -> ApiResponse[TranscriptionResponse]:
    """Update a transcription's text, status, or metadata."""
    transcription = await service.update(transcription_id, user.id, changes)
    return success(data=transcription, message="Transcription updated successfully")


async def delete_transcription(
    transcription_id: int,
    user: User = Depends(get_authorized_db_user),
    service: TranscriptionService = Depends(get_transcription_service),
) -> ApiResponse[None]:
    """Soft-delete a transcription."""
    await service.delete(transcription_id, user.id)
    return success(message="Transcription deleted successfully")
