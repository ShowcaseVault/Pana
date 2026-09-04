import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from api.config.config import settings


def create_access_token(data: dict, expires_minutes: int | None = None) -> str:
    expire_minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=expire_minutes)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_ACCESS_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict, expires_days: int | None = None) -> tuple[str, datetime]:
    """Mint a refresh token, returning it with the moment it expires.

    The expiry comes back because the token is recorded in the database and the
    stored row has to agree with the claim inside the token.

    A `jti` is added so every token is unique even when two are minted in the
    same second with the same claims: tokens are stored by hash under a unique
    index, and identical bytes would collide.
    """
    expire_days = expires_days or settings.REFRESH_TOKEN_EXPIRE_DAYS
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=expire_days)
    to_encode.update({"exp": expire, "type": "refresh", "jti": uuid.uuid4().hex})
    token = jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expire


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
