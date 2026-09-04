"""Database access for issued refresh tokens."""

import hashlib
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.refresh_tokens import RefreshToken


def hash_token(token: str) -> str:
    """Return the hex SHA-256 of a token.

    A plain hash, deliberately: unlike a password, the token is a 200-plus
    character random value, so there is nothing to brute-force and no need for
    a slow KDF -- which would add latency to every refresh.
    """
    return hashlib.sha256(token.encode()).hexdigest()


class RefreshTokenRepository:
    """Every read and write of the `refresh_tokens` table goes through here."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record(
        self,
        *,
        user_id: int,
        token: str,
        session_id: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """Store a newly issued token by hash."""
        row = RefreshToken(
            user_id=user_id,
            token_hash=hash_token(token),
            session_id=session_id,
            expires_at=expires_at,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return row

    async def get_by_token(self, token: str) -> RefreshToken | None:
        """Find the row for a token, whether or not it is still usable.

        Revoked and expired rows are returned too: the caller has to tell "no
        such token" apart from "a token that was already used", and only the
        second one means a replay.
        """
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == hash_token(token),
            RefreshToken.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_active(self, token: str) -> RefreshToken | None:
        """Find the row for a token only if it can still be exchanged."""
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == hash_token(token),
            RefreshToken.deleted_at.is_(None),
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(UTC),
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def revoke(
        self,
        row: RefreshToken,
        reason: str,
        *,
        replaced_by: str | None = None,
    ) -> None:
        """Revoke one token, optionally recording what replaced it."""
        row.revoked_at = datetime.now(UTC)
        row.revoked_reason = reason
        if replaced_by is not None:
            row.replaced_by_hash = hash_token(replaced_by)
        await self.db.flush()

    async def revoke_session(self, session_id: str, reason: str, *, commit: bool = False) -> int:
        """Revoke every live token in one rotation chain.

        A single UPDATE rather than a load-and-loop: this runs on the replay
        path, where the point is to shut the chain down immediately.

        `commit` is for the replay path, which revokes and then raises. The
        request-scoped session rolls back on an exception, so without its own
        commit the revocation would be undone and the stolen chain would stay
        live.
        """
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.session_id == session_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.deleted_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC), revoked_reason=reason)
        )
        result = await self.db.execute(stmt)
        if commit:
            await self.db.commit()
        else:
            await self.db.flush()
        return result.rowcount or 0

    async def revoke_all_for_user(self, user_id: int, reason: str) -> int:
        """Revoke every live token a user holds, on every device."""
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.deleted_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC), revoked_reason=reason)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount or 0

    async def delete_expired(self, *, before: datetime | None = None) -> int:
        """Soft-delete tokens that expired before `before` (default: now).

        Housekeeping: an expired token is already unusable, and the table would
        otherwise grow without bound. Soft delete keeps the audit trail, so a
        replay investigated later can still walk the chain.
        """
        cutoff = before or datetime.now(UTC)
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.expires_at < cutoff,
                RefreshToken.deleted_at.is_(None),
            )
            .values(deleted_at=datetime.now(UTC))
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount or 0
