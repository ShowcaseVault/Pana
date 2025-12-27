from fastapi import APIRouter, Depends, Response, Request, HTTPException
from fastapi.responses import RedirectResponse

from api.cruds.authentication import get_google_callback, get_google_login, get_auth_refresh, create_or_update_user, clear_auth_cookies
from api.schemas.return_response import SuccessResponse, FailureResponse
from api.auth.jwt_utils import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from api.auth.dependencies import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession

from api.connections.database_connection import get_async_db_session

from api.config.config import settings

CONFIG = settings

router = APIRouter(tags=["Authentication"])

@router.get("/auth/google")
def google_login():

    url = get_google_login()
    return RedirectResponse(url)

@router.get("/auth/google/callback")
async def google_callback(code: str, response: Response, db: AsyncSession = Depends(get_async_db_session)):
    try:
        user_info = get_google_callback(code)
        await create_or_update_user(db, user_info)
        
        # Token variables needed for token generation below
        sub = str(user_info.get("sub") or user_info.get("email") or "")
        email = str(user_info.get("email") or "")
        name = str(user_info.get("name") or "")

        # Token Generation
        access_token = create_access_token(
            {
                "sub": sub,
                "email": email,
                "name": name,
            }
        )
        refresh_token = create_refresh_token(
            {
                "sub": sub,
                "email": email,
            }
        )

        access_max_age = int(CONFIG.ACCESS_TOKEN_EXPIRE_MINUTES) * 60
        refresh_max_age = int(CONFIG.REFRESH_TOKEN_EXPIRE_DAYS) * 86400
        
        redirect_response = RedirectResponse(url=f"{CONFIG.CLIENT_URL}")

        redirect_response.set_cookie(
            CONFIG.ACCESS_COOKIE_NAME,
            access_token,
            httponly=True,
            secure=CONFIG.COOKIE_SECURE,
            samesite=CONFIG.COOKIE_SAMESITE,
            max_age=access_max_age,
        )
        redirect_response.set_cookie(
            CONFIG.REFRESH_COOKIE_NAME,
            refresh_token,
            httponly=True,
            secure=CONFIG.COOKIE_SECURE,
            samesite=CONFIG.COOKIE_SAMESITE,
            max_age=refresh_max_age,
        )

        return redirect_response

    except HTTPException as e:
        return RedirectResponse(f"{CONFIG.CLIENT_URL}/login?error={str(e.detail)}")
    except Exception:
        return RedirectResponse(f"{CONFIG.CLIENT_URL}/login?error=Google_Session_Failed")

@router.post("/auth/refresh")
def auth_refresh(request: Request, response: Response):
    try:
        token = request.cookies.get(CONFIG.REFRESH_COOKIE_NAME)
        if not token:
            auth = request.headers.get("authorization")
            if auth and auth.lower().startswith("bearer "):
                token = auth.split()[1]
        if not token:
            raise HTTPException(status_code=401, detail="Missing refresh token")

        new_access = get_auth_refresh(token)

        access_max_age = int(CONFIG.ACCESS_TOKEN_EXPIRE_MINUTES) * 60
        response.set_cookie(
            CONFIG.ACCESS_COOKIE_NAME,
            new_access,
            httponly=True,
            secure=CONFIG.COOKIE_SECURE,
            samesite=CONFIG.COOKIE_SAMESITE,
            max_age=access_max_age,
        )
        return SuccessResponse(
            data={"access_token": new_access, "token_type": "bearer"},
            message="Token refreshed",
        )
    except HTTPException as e:
        return FailureResponse(message=str(e.detail))
    except Exception:
        return FailureResponse(message="Refresh Failed")


@router.post("/auth/logout")
def auth_logout(response: Response):
    try:
        clear_auth_cookies(response)
        return SuccessResponse(data=None, message="Logged out")
    except Exception:
        return FailureResponse(message="Logout Failed")

