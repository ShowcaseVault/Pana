from fastapi import APIRouter, Body, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Union, Optional
from datetime import datetime, date

from api.schemas.return_response import SuccessResponse, FailureResponse
from api.auth.dependencies import get_authorized_db_user
from api.connections.database_connection import get_async_db_session
from api.cruds.recordings import (
    create_recording,
    get_all_recordings,
    get_recording_by_id,
    update_recording,
    delete_recording
)

from api.schemas.recordings import RecordingCreate,RecordingUpdate, RecordingResponse
from api.config.config import settings

router = APIRouter(prefix="/recordings", tags=["Recordings"])

@router.post("", response_model=Union[SuccessResponse, FailureResponse])
async def create_recording_endpoint(
    file: UploadFile = File(...),
    duration_seconds: int = Form(...),
    recorded_at: datetime = Form(...),
    location_text: str | None = Form(None),
    user = Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session)
):

    payload = RecordingCreate(
        duration_seconds=duration_seconds,
        recorded_at=recorded_at,
        location_text=location_text,
    )

    new_recording = await create_recording(
        db=db,
        file=file,
        user_id=user.id,
        user_sub=user.google_id,
        recording_data=payload
    )
    
    return SuccessResponse(data=new_recording, message="Recording created successfully")


@router.get("", response_model=Union[SuccessResponse, FailureResponse])
async def get_recordings_endpoint(
    skip: int = 0,
    limit: int = 100,
    recording_date: Optional[date] = None,
    list_all: Optional[bool] = False,
    user = Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session)
):
    recordings = await get_all_recordings(db, user.id, skip, limit, recording_date, list_all)
    return SuccessResponse(
        data=recordings,
        message="Recordings retrieved successfully"
    )


@router.get("/{recording_id}", response_model=Union[SuccessResponse, FailureResponse])
async def get_recording_endpoint(
    recording_id: int,
    user = Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session)
):
    recording = await get_recording_by_id(db, recording_id, user.id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
        
    return SuccessResponse(
        data=RecordingResponse.model_validate(recording),
        message="Recording retrieved successfully",
    )


@router.patch("/{recording_id}", response_model=Union[SuccessResponse, FailureResponse])
async def update_recording_endpoint(
    recording_id: int,
    update_data: RecordingUpdate,
    user = Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session)
):
    recording = await update_recording(db, recording_id, update_data, user.id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    return SuccessResponse(data=recording, message="Recording updated successfully")


@router.delete("/{recording_id}", response_model=Union[SuccessResponse, FailureResponse])
async def delete_recording_endpoint(
    recording_id: int,
    user = Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session)
):
    success = await delete_recording(db, recording_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Recording not found")
        
    return SuccessResponse(data=None, message="Recording deleted successfully")
