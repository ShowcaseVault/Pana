"""Home screen endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import get_current_user
from api.connections import get_async_db_session
from api.exceptions import error_docs
from api.repositories import UserRepository
from api.schemas.response import ApiResponse, success
from api.schemas.users import UserResponse
from api.services.home import HomeService

router = APIRouter(tags=["Home"])


def get_home_service(db: AsyncSession = Depends(get_async_db_session)) -> HomeService:
    """Build the home service with the repository it needs."""
    return HomeService(UserRepository(db))


@router.get("/home", responses=error_docs(401, 404))
async def get_home(
    current_user: dict = Depends(get_current_user),
    service: HomeService = Depends(get_home_service),
) -> ApiResponse[UserResponse]:
    """Return the signed-in user's profile."""
    profile = await service.get_profile(current_user["sub"])
    return success(data=profile, message="User profile retrieved successfully")
