from typing import Optional, Dict
from fastapi import Request, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.config.config import settings
from api.auth.jwt_utils import decode_access_token

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from api.connections.database_connection import get_async_db_session
from api.auth.get_user_by_sub import get_user_by_sub


CONFIG = settings

# Add security scheme for Swagger UI
security = HTTPBearer(auto_error=False)

def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def get_current_user(
    request: Request,
    token_auth: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Dict:
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
        token = request.cookies.get(CONFIG.ACCESS_COOKIE_NAME)

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_access_token(token)
        return payload
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

async def get_authorized_db_user(
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session)
) -> object:
    """
    Dependency that retrieves the user from the database based on the JWT 'sub' claim.
    Raises 401 if the user is not found (meaning token is valid but user is gone).
    """
    sub = current_user.get('sub')
    if not sub:
         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing sub claim")
         
    user = await get_user_by_sub(db, sub)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
    return user
