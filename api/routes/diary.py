from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import get_authorized_db_user
from api.connections import get_async_db_session
from api.cruds import diary as diary_crud
from api.schemas.return_response import FailureResponse, SuccessResponse

router = APIRouter(prefix="/diary", tags=["Diary"])


@router.post("", response_model=SuccessResponse | FailureResponse)
async def create_diary_endpoint(
    date: date | None = None,
    user=Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session),
):
    try:
        result = await diary_crud.create_or_update_diary(db, user.id, date)
        return SuccessResponse(
            data=result,
            message="Diary created/updated successfully",
        )
    except Exception as e:
        return FailureResponse(message=str(e))


@router.get("", response_model=SuccessResponse | FailureResponse)
async def get_diary_endpoint(
    date: date | None = None,
    user=Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session),
):
    try:
        result = await diary_crud.get_diary(db, user.id, date)
        return SuccessResponse(
            data=result,
            message="Diary fetched successfully",
        )
    except Exception as e:
        return FailureResponse(message=str(e))
