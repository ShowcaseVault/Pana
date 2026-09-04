from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.jwt_utils import (
    create_access_token,
    create_refresh_token,
)
from api.config.config import settings
from api.connections import get_async_db_session
from api.cruds.authentication import (
    clear_auth_cookies,
    create_or_update_user,
    get_auth_refresh,
    get_google_callback,
    get_google_login,
)
from api.exceptions import AppError, UnauthorizedError, error_docs
from api.schemas.response import ApiResponse

router = APIRouter(tags=["Authentication"])


@router.get("/auth/google")
def google_login():

    url = get_google_login()
    return RedirectResponse(url)


@router.get("/auth/google/callback")
async def google_callback(
    code: str, response: Response, db: AsyncSession = Depends(get_async_db_session)
):
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

        access_max_age = int(settings.ACCESS_TOKEN_EXPIRE_MINUTES) * 60
        refresh_max_age = int(settings.REFRESH_TOKEN_EXPIRE_DAYS) * 86400

        redirect_response = RedirectResponse(url=f"{settings.CLIENT_URL}")

        redirect_response.set_cookie(
            settings.ACCESS_COOKIE_NAME,
            access_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            max_age=access_max_age,
        )
        redirect_response.set_cookie(
            settings.REFRESH_COOKIE_NAME,
            refresh_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            max_age=refresh_max_age,
        )

        return redirect_response

    except AppError as e:
        # OAuth failures land in a browser mid-redirect, so the user goes back
        # to the login page with a reason rather than getting a JSON body.
        return RedirectResponse(f"{settings.CLIENT_URL}/login?error={e.message}")
    except Exception:
        return RedirectResponse(f"{settings.CLIENT_URL}/login?error=Google_Session_Failed")


@router.post("/auth/refresh", responses=error_docs(401))
def auth_refresh(request: Request, response: Response) -> ApiResponse[dict]:
    token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not token:
        auth = request.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            token = auth.split()[1]
    if not token:
        raise UnauthorizedError("Missing refresh token")

    new_access = get_auth_refresh(token)

    access_max_age = int(settings.ACCESS_TOKEN_EXPIRE_MINUTES) * 60
    response.set_cookie(
        settings.ACCESS_COOKIE_NAME,
        new_access,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=access_max_age,
    )
    return ApiResponse(
        data={"access_token": new_access, "token_type": "bearer"},
        message="Token refreshed",
    )


@router.post("/auth/logout")
def auth_logout(response: Response) -> ApiResponse[None]:
    clear_auth_cookies(response)
    return ApiResponse(data=None, message="Logged out")
