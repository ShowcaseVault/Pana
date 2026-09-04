from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import get_authorized_db_user
from api.connections import get_async_db_session
from api.cruds import diary as diary_crud
from api.exceptions import error_docs
from api.schemas.diary import DiaryResponse
from api.schemas.response import ApiResponse

router = APIRouter(prefix="/diary", tags=["Diary"])


@router.post("", responses=error_docs(401, 404))
async def create_diary_endpoint(
    date: date | None = None,
    user=Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ApiResponse[DiaryResponse]:
    result = await diary_crud.create_or_update_diary(db, user.id, date)
    return ApiResponse(data=result, message="Diary created/updated successfully")


@router.get("", responses=error_docs(401, 404))
async def get_diary_endpoint(
    date: date | None = None,
    user=Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ApiResponse[DiaryResponse]:
    result = await diary_crud.get_diary(db, user.id, date)
    return ApiResponse(data=result, message="Diary fetched successfully")
