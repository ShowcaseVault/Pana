from datetime import datetime, timedelta, timezone
from typing import Dict
from jose import jwt, JWTError

from api.config.config import settings

CONFIG = settings


def create_access_token(data: Dict, expires_minutes: int | None = None) -> str:
    expire_minutes = expires_minutes or CONFIG.ACCESS_TOKEN_EXPIRE_MINUTES
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, CONFIG.JWT_SECRET_KEY, algorithm=CONFIG.JWT_ALGORITHM)


def create_refresh_token(data: Dict, expires_days: int | None = None) -> str:
    expire_days = expires_days or CONFIG.REFRESH_TOKEN_EXPIRE_DAYS
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, CONFIG.JWT_REFRESH_SECRET_KEY, algorithm=CONFIG.JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict:
    payload = jwt.decode(token, CONFIG.JWT_SECRET_KEY, algorithms=[CONFIG.JWT_ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("Invalid token type")
    return payload


def decode_refresh_token(token: str) -> Dict:
    payload = jwt.decode(token, CONFIG.JWT_REFRESH_SECRET_KEY, algorithms=[CONFIG.JWT_ALGORITHM])
    if payload.get("type") != "refresh":
        raise JWTError("Invalid token type")
    return payload
