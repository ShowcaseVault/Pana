from typing import Union, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.return_response import SuccessResponse, FailureResponse
from api.auth.dependencies import get_authorized_db_user
from api.connections.database_connection import get_async_db_session

from api.schemas.history import HistoryFetch
from api.cruds import history as history_crud

router = APIRouter(prefix="/history", tags=["History"])

@router.get("/calendar/{year}/{month}", response_model=Union[SuccessResponse, FailureResponse])
async def fetch_calendar_endpoint(
    year: Optional[int] = None,
    month: Optional[int] = None,
    user = Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session),
):
    result = await history_crud.fetch_calendar(db,user.id, year, month)
    return SuccessResponse(
        data=result,
        message="Streak retrieved successfully"
    )

@router.post("", response_model=Union[SuccessResponse, FailureResponse])
async def fetch_history_endpoint(
    payload: HistoryFetch,
    user = Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session),
):
    result = await history_crud.fetch_history(db, user.id, payload)
    return SuccessResponse(
        data=result,
        message="History retrieved successfully",
    )
