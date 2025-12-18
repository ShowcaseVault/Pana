from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Union, Optional

from api.schemas.return_response import SuccessResponse, FailureResponse
from api.auth.dependencies import get_authorized_db_user
from api.connections.database_connection import get_async_db_session

from api.schemas.transcriptions import TranscriptionStatus
from api.cruds.transcriptions import (
    create_transcription,
    get_all_transcription,
    get_transcription_by_id,
    update_transcription,
    delete_transcription
)

from api.schemas.transcriptions import (
    TranscriptionCreate,
    TranscriptionUpdate,
    TranscriptionResponse,
)

router = APIRouter(prefix="/transcriptions", tags=["Transcriptions"])


# @router.post("", response_model=Union[SuccessResponse, FailureResponse])
async def create_transcription_endpoint(
    payload: TranscriptionCreate,
    user = Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session)
):

    new_transcription = await create_transcription(
        db=db,
        payload=payload,
        user_id=user.id,
    )
    if new_transcription is None:
        raise HTTPException(status_code=404, detail="Recording not found")
    if new_transcription is False:
        raise HTTPException(status_code=400, detail="Transcription already exists for this recording")
    
    return SuccessResponse(data=new_transcription, message="Transcription created successfully")


@router.get("", response_model=Union[SuccessResponse, FailureResponse])
async def get_transcriptions_endpoint(
    skip: int = 0,
    limit: int = 100,
    status: Optional[TranscriptionStatus] = None,
    user = Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session)
):
    status_value = status.value if status else None
    transcriptions = await get_all_transcription(db, skip, limit, user.id, status_value)
    return SuccessResponse(
        data=transcriptions,
        message="Transcriptions retrieved successfully"
    )


# @router.get("/{transcription_id}", response_model=Union[SuccessResponse, FailureResponse])
async def get_transcription_endpoint(
    transcription_id: int,
    user = Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session)
):
    transcription = await get_transcription_by_id(db, transcription_id, user.id)
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")
        
    return SuccessResponse(
        data=TranscriptionResponse.model_validate(transcription),
        message="Transcription retrieved successfully",
    )


# @router.patch("/{transcription_id}", response_model=Union[SuccessResponse, FailureResponse])
async def update_transcription_endpoint(
    transcription_id: int,
    update_data: TranscriptionUpdate,
    user = Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session)
):
    transcription = await update_transcription(db, transcription_id, update_data, user.id)
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    return SuccessResponse(data=transcription, message="Transcription updated successfully")


# @router.delete("/{transcription_id}", response_model=Union[SuccessResponse, FailureResponse])
async def delete_transcription_endpoint(
    transcription_id: int,
    user = Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session)
):
    success = await delete_transcription(db, transcription_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Transcription not found")
        
    return SuccessResponse(data=None, message="Transcription deleted successfully")
