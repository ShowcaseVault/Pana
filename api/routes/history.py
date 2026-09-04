from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import get_authorized_db_user
from api.connections import get_async_db_session
from api.cruds import history as history_crud
from api.exceptions import error_docs
from api.schemas.history import HistoryCalendar
from api.schemas.response import ApiResponse

router = APIRouter(prefix="/history", tags=["History"])


@router.get("/calendar/{year}/{month}", responses=error_docs(401))
async def fetch_calendar_endpoint(
    year: int | None = None,
    month: int | None = None,
    user=Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ApiResponse[HistoryCalendar]:
    result = await history_crud.fetch_calendar(db, user.id, year, month)
    return ApiResponse(data=result, message="Streak retrieved successfully")
