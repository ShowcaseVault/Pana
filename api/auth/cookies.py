"""Auth cookie handling.

Cookies are an HTTP detail, so they live beside the other auth plumbing rather
than in the service: the service issues tokens and does not know how they
travel.
"""

from fastapi import Response

from api.config.config import settings
from api.schemas.authentication import AuthTokens


def _set(response: Response, name: str, value: str, max_age: int) -> None:
    response.set_cookie(
        name,
        value,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=max_age,
    )


def set_access_cookie(response: Response, token: str, max_age: int) -> None:
    """Write the access token cookie."""
    _set(response, settings.ACCESS_COOKIE_NAME, token, max_age)


def set_auth_cookies(response: Response, tokens: AuthTokens) -> None:
    """Write both auth cookies from a freshly issued token pair."""
    set_access_cookie(response, tokens.access_token, tokens.access_max_age)
    _set(
        response,
        settings.REFRESH_COOKIE_NAME,
        tokens.refresh_token,
        tokens.refresh_max_age,
    )


def clear_auth_cookies(response: Response) -> None:
    """Remove both auth cookies.

    Deleted and then overwritten empty with max_age=0: delete_cookie omits the
    attributes the cookies were set with, and a browser ignores a deletion whose
    Secure and SameSite do not match.
    """
    for name in (settings.ACCESS_COOKIE_NAME, settings.REFRESH_COOKIE_NAME):
        response.delete_cookie(name)
        _set(response, name, "", 0)
