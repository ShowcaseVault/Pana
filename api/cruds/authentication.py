import requests
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from api.models.users import User

from fastapi import HTTPException
from fastapi import Response
from urllib.parse import urlencode
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from api.auth.jwt_utils import (
    create_access_token,
    decode_refresh_token,
)

from api.config.config import settings


CONFIG = settings


def clear_auth_cookies(response: Response) -> None:
    access_cookie = str(CONFIG.ACCESS_COOKIE_NAME)
    refresh_cookie = str(CONFIG.REFRESH_COOKIE_NAME)

    response.delete_cookie(access_cookie)
    response.delete_cookie(refresh_cookie)

    response.set_cookie(
        access_cookie,
        "",
        httponly=True,
        secure=CONFIG.COOKIE_SECURE,
        samesite=CONFIG.COOKIE_SAMESITE,
        max_age=0,
    )
    response.set_cookie(
        refresh_cookie,
        "",
        httponly=True,
        secure=CONFIG.COOKIE_SECURE,
        samesite=CONFIG.COOKIE_SAMESITE,
        max_age=0,
    )

def get_google_login():
    params = {
        "client_id": CONFIG.GOOGLE_CLIENT_ID,
        "redirect_uri": CONFIG.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "prompt": "consent",
        "access_type": "offline"
    }

    url = CONFIG.GOOGLE_AUTH_URL + "?" + urlencode(params)

    return url

def get_google_callback(code: str):

    token_url = CONFIG.GOOGLE_TOKEN_URL

    data = {
        "client_id": CONFIG.GOOGLE_CLIENT_ID,
        "client_secret": CONFIG.GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": CONFIG.GOOGLE_REDIRECT_URI,
    }

    token_response = requests.post(token_url, data=data).json()

    if "error" in token_response:
        raise HTTPException(status_code=400, detail=token_response)

    id_token = token_response["id_token"]

    try:
        user_info = google_id_token.verify_oauth2_token(
            id_token,
            google_requests.Request(),
            CONFIG.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=60
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="Could not get user info")
    
    return user_info

def get_auth_refresh(token: str):
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

    return new_access

async def create_or_update_user(db: AsyncSession, user_info: dict):
    # User Data
    sub = str(user_info.get("sub") or "")
    email = str(user_info.get("email") or "")
    name = str(user_info.get("name") or "")
    picture = str(user_info.get("picture") or "")

    # Database Interaction
    stmt = select(User).where(User.google_id == sub)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        user = User(
            google_id=sub,
            email=email,
            name=name,
            picture=picture
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        user.name = name
        user.picture = picture
        await db.commit()
        await db.refresh(user)
    
    return user