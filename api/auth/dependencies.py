from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.jwt_utils import decode_access_token
from api.auth.tokens import token_from_request
from api.config.config import settings
from api.connections import get_async_db_session
from api.exceptions import UnauthorizedError
from api.models.users import User
from api.repositories import UserRepository

# Add security scheme for Swagger UI
security = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    _swagger_auth: HTTPAuthorizationCredentials | None = Security(security),
) -> dict:
    """Return the access token's claims, from the header or the cookie.

    The `Security` parameter is what puts the padlock on the Swagger page; the
    token itself is read off the request, since `HTTPBearer` sees only the
    header and this accepts a cookie too.
    """
    token = token_from_request(request, settings.ACCESS_COOKIE_NAME)
    if not token:
        raise UnauthorizedError("Not authenticated")

    try:
        return decode_access_token(token)
    except Exception:
        raise UnauthorizedError("Invalid or expired token") from None


async def get_authorized_db_user(
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_async_db_session)
) -> User:
    """
    Dependency that retrieves the user from the database based on the JWT 'sub' claim.
    Raises 401 if the user is not found (meaning token is valid but user is gone).
    """
    sub = current_user.get("sub")
    if not sub:
        raise UnauthorizedError("Token missing sub claim")

    user = await UserRepository(db).get_by_google_id(sub)
    if not user:
        raise UnauthorizedError("User not found")

    return user
