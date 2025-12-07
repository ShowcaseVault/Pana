from fastapi import APIRouter, Depends, Response, Request, HTTPException

from api.cruds.authentication import get_google_callback
from api.schemas.return_response import SuccessResponse, FailureResponse
from api.auth.jwt_utils import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from api.auth.dependencies import get_current_user
from api.config.config import settings

CONFIG = settings

router = APIRouter()


@router.get("/auth/google/session")
def google_session(code: str, response: Response):
    try:
        user_info = get_google_callback(code)
        subject = str(user_info.get("sub") or user_info.get("email") or "")
        access_token = create_access_token(
            {
                "sub": subject,
                "email": user_info.get("email"),
                "name": user_info.get("name"),
            }
        )
        refresh_token = create_refresh_token(
            {
                "sub": subject,
                "email": user_info.get("email"),
            }
        )

        access_max_age = int(CONFIG.ACCESS_TOKEN_EXPIRE_MINUTES) * 60
        refresh_max_age = int(CONFIG.REFRESH_TOKEN_EXPIRE_DAYS) * 86400

        response.set_cookie(
            CONFIG.ACCESS_COOKIE_NAME,
            access_token,
            httponly=True,
            secure=CONFIG.COOKIE_SECURE,
            samesite=CONFIG.COOKIE_SAMESITE,
            max_age=access_max_age,
        )
        response.set_cookie(
            CONFIG.REFRESH_COOKIE_NAME,
            refresh_token,
            httponly=True,
            secure=CONFIG.COOKIE_SECURE,
            samesite=CONFIG.COOKIE_SAMESITE,
            max_age=refresh_max_age,
        )

        return SuccessResponse(
            data={
                "user": {
                    "sub": user_info.get("sub"),
                    "email": user_info.get("email"),
                    "name": user_info.get("name"),
                    "picture": user_info.get("picture"),
                },
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
            },
            message="Google Signin Success",
        )
    except HTTPException as e:
        return FailureResponse(message=str(e.detail))
    except Exception:
        return FailureResponse(message="Google Session Failed")


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

        payload = decode_refresh_token(token)
        subject = str(payload.get("sub") or "")
        new_access = create_access_token(
            {
                "sub": subject,
                "email": payload.get("email"),
            }
        )

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


@router.get("/me")
def me(current=Depends(get_current_user)):
    return SuccessResponse(data=current, message="Authenticated")
