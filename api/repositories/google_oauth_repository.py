"""Outbound calls to Google's OAuth endpoints.

The only place the application talks to Google. It returns the claims Google
gave us and nothing else: no tokens of our own, no database, no cookies.
"""

import logging
from typing import Any
from urllib.parse import urlencode

import anyio
import httpx
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from api.config.config import settings
from api.exceptions import ExternalServiceError, UnauthorizedError

logger = logging.getLogger("auth.google")

# The scopes the consent screen asks for. Fixed, not configurable: the rest of
# the login flow reads exactly these claims.
SCOPES = "openid email profile"


class GoogleOAuthRepository:
    """Google OAuth: build the consent URL, redeem a code, verify an id_token."""

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self.http_client = http_client

    def build_login_url(self) -> str:
        """Return the Google consent URL to redirect the browser to."""
        params = {
            "client_id": self._client_id(),
            "redirect_uri": self._required(settings.GOOGLE_REDIRECT_URI, "GOOGLE_REDIRECT_URI"),
            "response_type": "code",
            "scope": SCOPES,
            "prompt": "consent",
            "access_type": "offline",
        }
        auth_url = self._required(settings.GOOGLE_AUTH_URL, "GOOGLE_AUTH_URL")
        return f"{auth_url}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        """Trade an authorization code for Google's token response."""
        data = {
            "client_id": self._client_id(),
            "client_secret": self._required(settings.GOOGLE_CLIENT_SECRET, "GOOGLE_CLIENT_SECRET"),
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self._required(settings.GOOGLE_REDIRECT_URI, "GOOGLE_REDIRECT_URI"),
        }

        try:
            response = await self.http_client.post(
                self._required(settings.GOOGLE_TOKEN_URL, "GOOGLE_TOKEN_URL"),
                data=data,
            )
            payload = response.json()
        except httpx.HTTPError:
            logger.exception("Google token exchange request failed")
            raise ExternalServiceError("Could not reach Google to exchange the code") from None
        except ValueError:
            logger.error("Google token endpoint returned a non-JSON body")
            raise ExternalServiceError("Google token exchange returned an invalid body") from None

        if "error" in payload:
            # Google puts the reason in the body, so it is worth passing on --
            # it names the misconfiguration (redirect_uri_mismatch and friends).
            logger.warning("Google token exchange rejected: %s", payload.get("error"))
            raise ExternalServiceError("Google token exchange failed", data=payload)

        return payload

    async def verify_id_token(self, id_token: str) -> dict[str, Any]:
        """Verify an id_token's signature and audience, returning its claims.

        `google-auth` fetches Google's certificates with blocking `requests`, so
        the call runs in a worker thread: doing it inline would stall the event
        loop for the length of a network round trip on every login.

        Audience is checked here rather than by `verify_oauth2_token`, which
        takes a single value. Each client that can sign a user in -- the web
        client, and one per mobile platform -- mints tokens with its own `aud`,
        and all of them are legitimate. Passing `audience=None` skips only that
        one check; the signature, issuer, and expiry are still verified.
        """

        def _verify() -> dict[str, Any]:
            return google_id_token.verify_oauth2_token(
                id_token,
                google_requests.Request(),
                audience=None,
                # Google's clock and ours are never exactly aligned, and a
                # token issued a second "in the future" is not a failure.
                clock_skew_in_seconds=60,
            )

        try:
            claims = await anyio.to_thread.run_sync(_verify)
        except Exception:
            logger.exception("Google identity token verification failed")
            raise ExternalServiceError("Could not verify Google identity token") from None

        self._check_audience(claims)
        return claims

    def _check_audience(self, claims: dict[str, Any]) -> None:
        """Reject a token minted for some other application.

        Without this, any valid Google id_token from any project would be
        accepted -- including one an attacker obtained from an unrelated app --
        so this is what ties a token to us.
        """
        audience = claims.get("aud")
        allowed = self.allowed_audiences()

        if audience not in allowed:
            logger.warning("Rejected Google id_token for unexpected audience %r", audience)
            raise UnauthorizedError("Google token was issued for a different application")

    def allowed_audiences(self) -> set[str]:
        """Every Google client ID permitted to sign a user in."""
        return {self._client_id(), *settings.GOOGLE_MOBILE_CLIENT_IDS}

    def _client_id(self) -> str:
        return self._required(settings.GOOGLE_CLIENT_ID, "GOOGLE_CLIENT_ID")

    @staticmethod
    def _required(value: str | None, name: str) -> str:
        """Fail loudly on a missing Google setting.

        Each one defaults to None, so an unset variable would otherwise reach
        Google as the literal "None" and come back as an opaque OAuth error.
        """
        if not value:
            raise ExternalServiceError(f"Google OAuth is not configured: {name} is unset")
        return value
