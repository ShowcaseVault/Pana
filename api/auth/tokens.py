"""Pulling a token off a request.

Two transports carry tokens: a browser sends cookies, a native client sends
`Authorization: Bearer <token>`. Both endpoints that read a token accept either,
so the extraction lives here once rather than in each caller.
"""

from fastapi import Request


def bearer_token(authorization: str | None) -> str | None:
    """Return the credentials from an `Authorization: Bearer <token>` header."""
    if not authorization:
        return None
    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credentials.strip():
        return None
    return credentials.strip()


def token_from_request(request: Request, cookie_name: str) -> str | None:
    """Return the token from the Authorization header, else the named cookie.

    The header wins: a client that sets it explicitly means it, and a stale
    cookie left over in the same browser should not shadow that choice.
    """
    return bearer_token(request.headers.get("authorization")) or request.cookies.get(cookie_name)
