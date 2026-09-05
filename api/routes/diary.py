"""Diary endpoints."""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import get_authorized_db_user
from api.connections import get_async_db_session, get_groq_client, get_http_client
from api.exceptions import error_docs
from api.models.users import User
from api.repositories import (
    DiaryAIRepository,
    DiaryRepository,
    LocationRepository,
    TranscriptionRepository,
)
from api.schemas.diary import DiaryResponse
from api.schemas.response import ApiResponse
from api.services.diary import DiaryService
from celery_service.tasks.transcription import transcribe_audio_task

router = APIRouter(prefix="/diary", tags=["Diary"])


def get_diary_service(
    db: AsyncSession = Depends(get_async_db_session),
) -> DiaryService:
    """Build the diary service with the repositories it needs."""
    return DiaryService(
        diaries=DiaryRepository(db),
        transcriptions=TranscriptionRepository(db),
        location=LocationRepository(get_http_client()),
        diary_ai=DiaryAIRepository(get_groq_client()),
    )


@router.post("", responses=error_docs(401, 404))
async def generate_diary(
    date: date | None = None,
    user: User = Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session),
    service: DiaryService = Depends(get_diary_service),
) -> ApiResponse[DiaryResponse]:
    """Write or rewrite the diary for a day. Defaults to today."""
    diary, pending_transcriptions = await service.generate(user.id, date)

    if pending_transcriptions:
        # Commit before dispatching: the workers run in other processes and
        # would not see rows still sitting in this request's transaction.
        await db.commit()
        for transcription_id in pending_transcriptions:
            transcribe_audio_task.apply_async(args=[transcription_id], queue="high_priority")

    return ApiResponse(data=diary, message="Diary created/updated successfully")


@router.get("", responses=error_docs(401, 404))
async def get_diary(
    date: date | None = None,
    user: User = Depends(get_authorized_db_user),
    service: DiaryService = Depends(get_diary_service),
) -> ApiResponse[DiaryResponse]:
    """Return the diary for a day, empty if it has not been written yet."""
    diary = await service.get(user.id, date)
    return ApiResponse(data=diary, message="Diary fetched successfully")
