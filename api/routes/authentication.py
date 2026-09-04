"""Authentication endpoints.

Routes do three things: read the request, call the service, shape the response.
Data access lives in the repositories the service holds.
"""

import logging

import httpx
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.cookies import clear_auth_cookies, set_access_cookie, set_auth_cookies
from api.auth.tokens import token_from_request
from api.config.config import settings
from api.connections import get_async_db_session, get_http_client
from api.exceptions import AppError, UnauthorizedError, error_docs
from api.repositories import GoogleOAuthRepository, UserRepository
from api.schemas.authentication import AccessToken
from api.schemas.response import ApiResponse
from api.services.authentication import AuthService

logger = logging.getLogger("auth")

router = APIRouter(tags=["Authentication"])


# ── Dependencies ─────────────────────────────────────────────────────────────


def get_auth_service(
    db: AsyncSession = Depends(get_async_db_session),
    http_client: httpx.AsyncClient = Depends(get_http_client),
) -> AuthService:
    """Build the auth service with the repositories it needs."""
    return AuthService(
        user_repository=UserRepository(db),
        oauth_repository=GoogleOAuthRepository(http_client),
    )


def get_token_service(
    http_client: httpx.AsyncClient = Depends(get_http_client),
) -> AuthService:
    """The auth service without a database session.

    Building the consent URL and refreshing an access token touch no rows, so
    these routes must not check out a connection from the pool to serve a
    request that would never use it.
    """
    return AuthService(
        user_repository=None,
        oauth_repository=GoogleOAuthRepository(http_client),
    )


# ── Routes ───────────────────────────────────────────────────────────────────


@router.get("/auth/google")
def google_login(service: AuthService = Depends(get_token_service)) -> RedirectResponse:
    """Send the browser to Google's consent screen."""
    return RedirectResponse(service.google_login_url())


@router.get("/auth/google/callback")
async def google_callback(
    code: str,
    service: AuthService = Depends(get_auth_service),
) -> RedirectResponse:
    """Complete the Google flow, set the auth cookies, and return to the client."""
    try:
        tokens = await service.login_with_google(code)
    except AppError as e:
        # This lands in a browser mid-redirect, so the user goes back to the
        # login page with a reason rather than getting a JSON body.
        logger.warning("Google callback failed: %s", e.message)
        return RedirectResponse(f"{settings.CLIENT_URL}/login?error={e.message}")
    except Exception:
        logger.exception("Unhandled error in Google callback")
        return RedirectResponse(f"{settings.CLIENT_URL}/login?error=Google_Session_Failed")

    response = RedirectResponse(url=settings.CLIENT_URL)
    set_auth_cookies(response, tokens)
    return response


@router.post("/auth/refresh", responses=error_docs(401))
def auth_refresh(
    request: Request,
    response: Response,
    service: AuthService = Depends(get_token_service),
) -> ApiResponse[AccessToken]:
    """Reissue an access token from the refresh token."""
    token = token_from_request(request, settings.REFRESH_COOKIE_NAME)
    if not token:
        raise UnauthorizedError("Missing refresh token")

    access_token = service.refresh_access_token(token)
    set_access_cookie(response, access_token, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)

    return ApiResponse(
        data=AccessToken(access_token=access_token),
        message="Token refreshed",
    )


@router.post("/auth/logout")
def auth_logout(response: Response) -> ApiResponse[None]:
    """Drop both auth cookies. No service call: nothing server-side to revoke."""
    clear_auth_cookies(response)
    return ApiResponse(data=None, message="Logged out")
