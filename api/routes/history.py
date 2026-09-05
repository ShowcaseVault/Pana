"""History endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import get_authorized_db_user
from api.connections import get_async_db_session
from api.exceptions import error_docs
from api.models.users import User
from api.repositories import HistoryRepository
from api.schemas.history import HistoryCalendar
from api.schemas.response import ApiResponse
from api.services.history import HistoryService

router = APIRouter(prefix="/history", tags=["History"])


def get_history_service(
    db: AsyncSession = Depends(get_async_db_session),
) -> HistoryService:
    """Build the history service with the repository it needs."""
    return HistoryService(HistoryRepository(db))


@router.get("/calendar/{year}/{month}", responses=error_docs(401))
async def get_calendar(
    year: int,
    month: int,
    user: User = Depends(get_authorized_db_user),
    service: HistoryService = Depends(get_history_service),
) -> ApiResponse[HistoryCalendar]:
    """Return the days of a month the user has diaries or recordings on."""
    result = await service.calendar(user.id, year, month)
    return ApiResponse(data=result, message="Calendar retrieved successfully")
