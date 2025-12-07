from typing import Optional, Dict
from fastapi import Request, HTTPException, status

from api.config.config import settings
from api.auth.jwt_utils import decode_access_token

CONFIG = settings


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def get_current_user(request: Request) -> Dict:
    """
    Reads access token from Authorization: Bearer <token> header, or from cookie.
    Decodes and returns JWT payload. Raises 401 if missing/invalid.
    """
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
