from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.get_user_by_sub import get_user_by_sub
from api.auth.jwt_utils import decode_access_token
from api.config.config import settings
from api.connections import get_async_db_session
from api.exceptions import UnauthorizedError

# Add security scheme for Swagger UI
security = HTTPBearer(auto_error=False)


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def get_current_user(
    request: Request, token_auth: HTTPAuthorizationCredentials | None = Security(security)
) -> dict:
    """
    Reads access token from Authorization: Bearer <token> header, or from cookie.
    Decodes and returns JWT payload. Raises 401 if missing/invalid.
    """
    token = None
    if token_auth:
        token = token_auth.credentials

    if not token:
        token = _extract_bearer_token(request.headers.get("authorization"))

    if not token:
        token = request.cookies.get(settings.ACCESS_COOKIE_NAME)

    if not token:
        raise UnauthorizedError("Not authenticated")

    try:
        payload = decode_access_token(token)
        return payload
    except Exception:
        raise UnauthorizedError("Invalid or expired token") from None


async def get_authorized_db_user(
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_async_db_session)
) -> object:
    """
    Dependency that retrieves the user from the database based on the JWT 'sub' claim.
    Raises 401 if the user is not found (meaning token is valid but user is gone).
    """
    sub = current_user.get("sub")
    if not sub:
        raise UnauthorizedError("Token missing sub claim")

    user = await get_user_by_sub(db, sub)
    if not user:
        raise UnauthorizedError("User not found")

    return user
