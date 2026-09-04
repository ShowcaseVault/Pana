from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import get_current_user
from api.connections import get_async_db_session
from api.cruds.home import get_user_profile
from api.exceptions import error_docs
from api.schemas.response import ApiResponse
from api.schemas.users import UserResponse

router = APIRouter(tags=["Home"])


@router.get("/home", responses=error_docs(401, 404))
async def get_home(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> ApiResponse[UserResponse]:
    # current_user holds the decoded JWT payload from the dependency.
    google_id = current_user.get("sub")
    user_profile = await get_user_profile(db, google_id)
    return ApiResponse(data=user_profile, message="User profile retrieved successfully")
