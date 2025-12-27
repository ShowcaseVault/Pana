from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.return_response import SuccessResponse, FailureResponse
from api.auth.dependencies import get_current_user
from api.connections.database_connection import get_async_db_session
from api.cruds.home import get_user_profile

router = APIRouter(tags=["Home"])

@router.get("/home")
async def get_home(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session)
):
    try:
        # current_user from get_current_user dependency contains the decoded JWT payload
        google_id = current_user.get("sub")
        
        user_profile = await get_user_profile(db, google_id)
        
        return SuccessResponse(
            data=user_profile,
            message="User profile retrieved successfully"
        )
    except Exception as e:
        return FailureResponse(message=str(e))
