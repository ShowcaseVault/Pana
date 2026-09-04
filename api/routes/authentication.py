"""Authentication endpoints.

Routes do three things: read the request, call the service, shape the response.
Data access lives in the repositories the service holds.
"""

import logging

import httpx
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.cookies import clear_auth_cookies, set_auth_cookies
from api.auth.tokens import token_from_request
from api.config.config import settings
from api.connections import get_async_db_session, get_http_client
from api.exceptions import AppError, UnauthorizedError, error_docs
from api.repositories import (
    GoogleOAuthRepository,
    RefreshTokenRepository,
    UserRepository,
)
from api.schemas.authentication import (
    AuthTokens,
    GoogleIdTokenRequest,
    RefreshTokenRequest,
)
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
        token_repository=RefreshTokenRepository(db),
        oauth_repository=GoogleOAuthRepository(http_client),
    )


def get_oauth_service(
    http_client: httpx.AsyncClient = Depends(get_http_client),
) -> AuthService:
    """The auth service without a database session.

    Only the consent URL is built this way: it touches no rows, so the route
    must not check a connection out of the pool to serve a request that would
    never use it. Every other auth route reads or writes tokens.
    """
    return AuthService(oauth_repository=GoogleOAuthRepository(http_client))


# ── Browser routes: tokens travel in httpOnly cookies ────────────────────────


@router.get("/auth/google")
def google_login(service: AuthService = Depends(get_oauth_service)) -> RedirectResponse:
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
async def auth_refresh(
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[None]:
    """Rotate the session: spend the refresh token, set a fresh pair.

    Both cookies are replaced, since rotation issues a new refresh token as
    well. The body carries no tokens -- a browser client reads them from the
    cookies it cannot see, and putting them in JSON would only expose them to
    scripts.
    """
    token = token_from_request(request, settings.REFRESH_COOKIE_NAME)
    if not token:
        raise UnauthorizedError("Missing refresh token")

    tokens = await service.rotate_refresh_token(token)
    set_auth_cookies(response, tokens)

    return ApiResponse(data=None, message="Token refreshed")


@router.post("/auth/logout")
async def auth_logout(
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[None]:
    """Revoke this session and clear the cookies.

    The refresh token is revoked server-side, so a copy taken from the browser
    beforehand is dead too. The access token stays valid until it expires --
    minutes, by design, which is the trade for not checking the database on
    every request.
    """
    token = token_from_request(request, settings.REFRESH_COOKIE_NAME)
    await service.logout(token)
    clear_auth_cookies(response)
    return ApiResponse(data=None, message="Logged out")


# ── Native routes: tokens travel in the body, for the device keychain ────────
#
# A mobile app completes Google sign-in through the platform SDK, so there is
# no redirect and no authorization code to redeem -- it posts the id_token it
# already holds. Nothing here sets a cookie: the app stores both tokens itself
# and sends the access token as `Authorization: Bearer <token>`.


@router.post("/auth/mobile/google", responses=error_docs(401, 502))
async def mobile_google_login(
    payload: GoogleIdTokenRequest,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[AuthTokens]:
    """Exchange a Google id_token from a native SDK for our own token pair."""
    tokens = await service.login_with_google_id_token(payload.id_token)
    return ApiResponse(data=tokens, message="Logged in")


@router.post("/auth/mobile/refresh", responses=error_docs(401))
async def mobile_auth_refresh(
    payload: RefreshTokenRequest,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[AuthTokens]:
    """Rotate the session, returning a new pair for the device to store.

    The refresh token sent here is spent. The app must replace both stored
    tokens with the ones returned, or its next refresh looks like a replay and
    the session is revoked.
    """
    tokens = await service.rotate_refresh_token(payload.refresh_token)
    return ApiResponse(data=tokens, message="Token refreshed")


@router.post("/auth/mobile/logout", responses=error_docs(401))
async def mobile_auth_logout(
    payload: RefreshTokenRequest,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[None]:
    """Revoke the session a device's refresh token belongs to."""
    await service.logout(payload.refresh_token)
    return ApiResponse(data=None, message="Logged out")
