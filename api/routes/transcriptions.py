from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import get_authorized_db_user
from api.connections import get_async_db_session
from api.cruds.transcriptions import (
    create_transcription,
    delete_transcription,
    get_all_transcription,
    get_transcription_by_id,
    update_transcription,
)
from api.exceptions import BadRequestError, NotFoundError, error_docs
from api.schemas.response import ApiResponse
from api.schemas.transcriptions import (
    TranscriptionCreate,
    TranscriptionResponse,
    TranscriptionStatus,
    TranscriptionUpdate,
)

router = APIRouter(prefix="/transcriptions", tags=["Transcriptions"])


# @router.post("", responses=error_docs(400, 401, 404))
async def create_transcription_endpoint(
    payload: TranscriptionCreate,
    user=Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ApiResponse[TranscriptionResponse]:
    new_transcription = await create_transcription(
        db=db,
        payload=payload,
        user_id=user.id,
    )
    if new_transcription is None:
        raise NotFoundError("Recording not found")
    if new_transcription is False:
        raise BadRequestError("Transcription already exists for this recording")

    return ApiResponse(data=new_transcription, message="Transcription created successfully")


@router.get("", responses=error_docs(401))
async def get_transcriptions_endpoint(
    skip: int = 0,
    limit: int = 100,
    status: TranscriptionStatus | None = None,
    user=Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ApiResponse[list[TranscriptionResponse]]:
    status_value = status.value if status else None
    transcriptions = await get_all_transcription(db, skip, limit, user.id, status_value)
    return ApiResponse(data=transcriptions, message="Transcriptions retrieved successfully")


@router.get("/{transcription_id}", responses=error_docs(401, 404))
async def get_transcription_endpoint(
    transcription_id: int,
    user=Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ApiResponse[TranscriptionResponse]:
    transcription = await get_transcription_by_id(db, transcription_id, user.id)
    if not transcription:
        raise NotFoundError("Transcription not found")

    return ApiResponse(
        data=TranscriptionResponse.model_validate(transcription),
        message="Transcription retrieved successfully",
    )


# @router.patch("/{transcription_id}", responses=error_docs(401, 404))
async def update_transcription_endpoint(
    transcription_id: int,
    update_data: TranscriptionUpdate,
    user=Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ApiResponse[TranscriptionResponse]:
    transcription = await update_transcription(db, transcription_id, update_data, user.id)
    if not transcription:
        raise NotFoundError("Transcription not found")

    return ApiResponse(data=transcription, message="Transcription updated successfully")


# @router.delete("/{transcription_id}", responses=error_docs(401, 404))
async def delete_transcription_endpoint(
    transcription_id: int,
    user=Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ApiResponse[None]:
    deleted = await delete_transcription(db, transcription_id, user.id)
    if not deleted:
        raise NotFoundError("Transcription not found")

    return ApiResponse(data=None, message="Transcription deleted successfully")
