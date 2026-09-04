from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from api.config.config import settings


def create_access_token(data: dict, expires_minutes: int | None = None) -> str:
    expire_minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=expire_minutes)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_ACCESS_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict, expires_days: int | None = None) -> str:
    expire_days = expires_days or settings.REFRESH_TOKEN_EXPIRE_DAYS
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, settings.JWT_ACCESS_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("Invalid token type")
    return payload


def decode_refresh_token(token: str) -> dict:
    payload = jwt.decode(
        token, settings.JWT_REFRESH_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    if payload.get("type") != "refresh":
        raise JWTError("Invalid token type")
    return payload
