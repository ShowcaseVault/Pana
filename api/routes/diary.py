from typing import Union
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.return_response import SuccessResponse, FailureResponse
from api.auth.dependencies import get_authorized_db_user
from api.connections.database_connection import get_async_db_session

from api.schemas.diary import DiaryResponse
from api.cruds import diary as diary_crud

router = APIRouter(prefix="/diary", tags=["Diary"])


@router.post("", response_model=Union[SuccessResponse, FailureResponse])
async def create_today_diary_endpoint(
    user = Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session),
):
    try:
        result = await diary_crud.create_or_update_today_diary(db, user.id)
        return SuccessResponse(
            data=result,
            message="Diary created/updated successfully",
        )
    except Exception as e:
        return FailureResponse(message=str(e))
