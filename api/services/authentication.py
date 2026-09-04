"""Authentication business logic.

Owns the login flow: what Google says, what we store, what tokens we issue.
Everything HTTP-shaped -- redirects, cookies, status codes -- stays in the
route; everything external stays in the repositories.
"""

import logging

from api.auth.jwt_utils import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from api.config.config import settings
from api.exceptions import UnauthorizedError
from api.models.users import User
from api.repositories import GoogleOAuthRepository, UserRepository
from api.schemas.authentication import AuthTokens, GoogleProfile

logger = logging.getLogger("auth")


class AuthService:
    """Google login, user upsert, and token issue and refresh."""

    def __init__(
        self,
        *,
        oauth_repository: GoogleOAuthRepository,
        user_repository: UserRepository | None = None,
    ) -> None:
        # The user repository is optional: issuing the consent URL and
        # refreshing an access token never touch a row, and those routes build
        # the service without a database session rather than checking a
        # connection out of the pool to leave it unused.
        self._user_repository = user_repository
        self.oauth_repository = oauth_repository

    @property
    def user_repository(self) -> UserRepository:
        """The user repository, or a clear error if this service has none."""
        if self._user_repository is None:
            raise RuntimeError("AuthService was built without a UserRepository")
        return self._user_repository

    def google_login_url(self) -> str:
        """Where to send the browser to start the Google consent flow."""
        return self.oauth_repository.build_login_url()

    async def login_with_google(self, code: str) -> AuthTokens:
        """Complete the OAuth callback: redeem the code, upsert, issue tokens."""
        token_response = await self.oauth_repository.exchange_code(code)

        id_token = token_response.get("id_token")
        if not id_token:
            raise UnauthorizedError("Google response contained no identity token")

        claims = await self.oauth_repository.verify_id_token(id_token)
        profile = self._profile_from_claims(claims)

        user = await self._upsert_user(profile)
        logger.info("Google login succeeded for user id=%s", user.id)

        return self.issue_tokens(profile)

    def issue_tokens(self, profile: GoogleProfile) -> AuthTokens:
        """Mint an access and refresh token pair for a verified profile."""
        access_token = create_access_token(
            {
                "sub": profile.sub,
                "email": profile.email,
                "name": profile.name or "",
            }
        )
        # The refresh token carries only what reissuing an access token needs,
        # since it lives far longer than the access token does.
        refresh_token = create_refresh_token(
            {
                "sub": profile.sub,
                "email": profile.email,
            }
        )

        return AuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            access_max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        )

    def refresh_access_token(self, refresh_token: str) -> str:
        """Reissue an access token from a valid refresh token."""
        if not refresh_token:
            raise UnauthorizedError("Missing refresh token")

        try:
            payload = decode_refresh_token(refresh_token)
        except Exception:
            raise UnauthorizedError("Invalid or expired refresh token") from None

        subject = str(payload.get("sub") or "")
        if not subject:
            raise UnauthorizedError("Refresh token missing sub claim")

        return create_access_token(
            {
                "sub": subject,
                "email": payload.get("email"),
            }
        )

    async def _upsert_user(self, profile: GoogleProfile) -> User:
        """Create the user on first login, or refresh what Google owns."""
        user = await self.user_repository.get_by_google_id(profile.sub)

        if user is None:
            return await self.user_repository.create(
                google_id=profile.sub,
                email=profile.email,
                name=profile.name,
                picture=profile.picture,
            )

        # Name and picture are Google's to change; email and google_id identify
        # the row and are left alone.
        return await self.user_repository.update_profile(
            user,
            name=profile.name,
            picture=profile.picture,
        )

    @staticmethod
    def _profile_from_claims(claims: dict) -> GoogleProfile:
        """Narrow Google's verified claims down to the fields we rely on."""
        sub = str(claims.get("sub") or "")
        email = str(claims.get("email") or "")
        if not sub or not email:
            raise UnauthorizedError("Google profile is missing a subject or an email")

        return GoogleProfile(
            sub=sub,
            email=email,
            name=claims.get("name"),
            picture=claims.get("picture"),
        )
