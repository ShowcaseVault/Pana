"""Authentication business logic.

Owns the login flow: what Google says, what we store, what tokens we issue.
Everything HTTP-shaped -- redirects, cookies, status codes -- stays in the
route; everything external stays in the repositories.
"""

import logging
import uuid

from api.auth.jwt_utils import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from api.config.config import settings
from api.exceptions import UnauthorizedError
from api.models.users import User
from api.repositories import (
    GoogleOAuthRepository,
    RefreshTokenRepository,
    UserRepository,
)
from api.schemas.authentication import AuthTokens, GoogleProfile

logger = logging.getLogger("auth")


class AuthService:
    """Google login, user upsert, and token issue and refresh."""

    def __init__(
        self,
        *,
        oauth_repository: GoogleOAuthRepository,
        user_repository: UserRepository | None = None,
        token_repository: RefreshTokenRepository | None = None,
    ) -> None:
        # Both database repositories are optional: building the consent URL
        # touches no rows, so that route constructs the service without a
        # session rather than checking a connection out of the pool to leave it
        # unused. Refreshing does need one, now that tokens are stored.
        self._user_repository = user_repository
        self._token_repository = token_repository
        self.oauth_repository = oauth_repository

    @property
    def user_repository(self) -> UserRepository:
        """The user repository, or a clear error if this service has none."""
        if self._user_repository is None:
            raise RuntimeError("AuthService was built without a UserRepository")
        return self._user_repository

    @property
    def token_repository(self) -> RefreshTokenRepository:
        """The refresh-token repository, or a clear error if there is none."""
        if self._token_repository is None:
            raise RuntimeError("AuthService was built without a RefreshTokenRepository")
        return self._token_repository

    def google_login_url(self) -> str:
        """Where to send the browser to start the Google consent flow."""
        return self.oauth_repository.build_login_url()

    async def login_with_google(self, code: str) -> AuthTokens:
        """Browser entry: redeem the authorization code, then authenticate.

        The web client cannot hold the Google client secret, so it gets an
        authorization code and this redeems it server-side for the id_token
        that a native app already holds.
        """
        token_response = await self.oauth_repository.exchange_code(code)

        id_token = token_response.get("id_token")
        if not id_token:
            raise UnauthorizedError("Google response contained no identity token")

        return await self.login_with_google_id_token(id_token)

    async def login_with_google_id_token(self, id_token: str) -> AuthTokens:
        """Native entry: authenticate an id_token the app's Google SDK issued.

        No code exchange: the platform SDK has already completed the flow, and
        the app posts the resulting id_token directly. Verification is what
        makes this safe to accept from an untrusted client -- the token is
        signed by Google and its audience must be one of ours.
        """
        claims = await self.oauth_repository.verify_id_token(id_token)
        return await self._authenticate(self._profile_from_claims(claims))

    async def _authenticate(self, profile: GoogleProfile) -> AuthTokens:
        """Turn a verified Google profile into a user and a token pair.

        Both entry points converge here, so web and mobile cannot drift apart
        on what a login actually does.
        """
        user = await self._upsert_user(profile)

        # Each login opens its own session family. Rotation keeps refreshing
        # within one family, so revoking it later logs out this device alone.
        tokens = await self._issue_session(user, profile, session_id=uuid.uuid4().hex)
        logger.info("Google login succeeded for user id=%s", user.id)
        return tokens

    async def _issue_session(
        self,
        user: User,
        profile: GoogleProfile,
        *,
        session_id: str,
    ) -> AuthTokens:
        """Mint a token pair and record the refresh token as live."""
        access_token = create_access_token(
            {
                "sub": profile.sub,
                "email": profile.email,
                "name": profile.name or "",
            }
        )
        # The refresh token carries only what reissuing an access token needs,
        # since it lives far longer than the access token does.
        refresh_token, expires_at = create_refresh_token(
            {
                "sub": profile.sub,
                "email": profile.email,
                "session_id": session_id,
            }
        )

        # Recorded before the response goes out: a token the client holds but
        # the database never saw would be rejected on first use.
        await self.token_repository.record(
            user_id=user.id,
            token=refresh_token,
            session_id=session_id,
            expires_at=expires_at,
        )

        return AuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            access_max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        )

    async def rotate_refresh_token(self, refresh_token: str) -> AuthTokens:
        """Exchange a refresh token for a new pair, revoking the old one.

        Rotation is what limits the damage of a stolen refresh token: each one
        works exactly once, so a thief's copy is either useless (the real client
        refreshed first) or detectable (the thief refreshed first, and the real
        client's next attempt is a replay).
        """
        if not refresh_token:
            raise UnauthorizedError("Missing refresh token")

        try:
            payload = decode_refresh_token(refresh_token)
        except Exception:
            raise UnauthorizedError("Invalid or expired refresh token") from None

        subject = str(payload.get("sub") or "")
        if not subject:
            raise UnauthorizedError("Refresh token missing sub claim")

        stored = await self.token_repository.get_by_token(refresh_token)

        if stored is None:
            # Signature is valid but we never issued this, or housekeeping has
            # already removed it. Either way there is nothing to rotate.
            logger.warning("Refresh token not on record for sub=%s", subject)
            raise UnauthorizedError("Refresh token is no longer valid")

        if stored.revoked_at is not None:
            # A token used twice. One of the two holders is an attacker and
            # there is no way to tell which, so the whole family goes.
            # Committed here, not left to the request: this path raises, and a
            # rolled-back revocation would leave the stolen chain usable.
            revoked = await self.token_repository.revoke_session(
                stored.session_id, "reuse_detected", commit=True
            )
            logger.warning(
                "Refresh token replay for user id=%s: revoked %d token(s) in session %s",
                stored.user_id,
                revoked,
                stored.session_id,
            )
            raise UnauthorizedError("Refresh token has already been used")

        user = await self.user_repository.get_by_google_id(subject)
        if user is None:
            raise UnauthorizedError("User not found")

        profile = GoogleProfile(sub=subject, email=user.email, name=user.name)
        tokens = await self._issue_session(user, profile, session_id=stored.session_id)

        # Only now is the presented token spent, and it points at its successor
        # so the chain can be walked when investigating a replay.
        await self.token_repository.revoke(stored, "rotated", replaced_by=tokens.refresh_token)

        return tokens

    async def logout(self, refresh_token: str | None) -> None:
        """Revoke the session a refresh token belongs to.

        Best effort by design: a client that has already lost its token still
        gets a successful logout, since there is nothing useful to tell it and
        nothing left to revoke.
        """
        if not refresh_token:
            return

        stored = await self.token_repository.get_by_token(refresh_token)
        if stored is None:
            return

        revoked = await self.token_repository.revoke_session(stored.session_id, "logout")
        logger.info("Logout revoked %d token(s) for user id=%s", revoked, stored.user_id)

    async def logout_everywhere(self, user: User) -> int:
        """Revoke every session a user holds, on every device."""
        revoked = await self.token_repository.revoke_all_for_user(user.id, "logout_all")
        logger.info("Revoked %d token(s) for user id=%s across all devices", revoked, user.id)
        return revoked

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
