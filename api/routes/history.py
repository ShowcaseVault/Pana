from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import get_authorized_db_user
from api.connections.database_connection import get_async_db_session
from api.cruds import history as history_crud
from api.schemas.return_response import FailureResponse, SuccessResponse

router = APIRouter(prefix="/history", tags=["History"])


@router.get("/calendar/{year}/{month}", response_model=SuccessResponse | FailureResponse)
async def fetch_calendar_endpoint(
    year: int | None = None,
    month: int | None = None,
    user=Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session),
):
    result = await history_crud.fetch_calendar(db, user.id, year, month)
    return SuccessResponse(data=result, message="Streak retrieved successfully")
