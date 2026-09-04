"""Issued refresh tokens, so they can be rotated and revoked.

Access tokens stay stateless -- they are short-lived and checked by signature
alone. Refresh tokens are the long-lived credential, and a stateless one cannot
be taken back: a stolen token would work until it expired. Recording each one
issued is what makes logout and theft response possible.

Only a hash of the token is stored. A dump of this table is then worthless to
an attacker, the same reason a password table holds no passwords.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import BaseModel

if TYPE_CHECKING:
    from api.models.users import User


class RefreshToken(BaseModel):
    """One issued refresh token, live until used, revoked, or expired.

    Rows form a chain: refreshing revokes the presented token and issues its
    successor, all sharing a `session_id`. That family is the unit of trust --
    when a token is replayed, the whole chain is burned, because there is no way
    to tell the thief's copy from the legitimate one.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # SHA-256 of the token, hex encoded: 64 characters, always. Unique, so the
    # same token can never be recorded twice.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    # Groups every token in one login's rotation chain. Indexed because
    # revoking a family is a write against this column.
    session_id: Mapped[str] = mapped_column(String(64), index=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    # NULL while the token is usable. Set when it is rotated away, logged out,
    # or burned after a replay -- `revoked_reason` says which.
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_reason: Mapped[str | None] = mapped_column(String(32))

    # What the token was traded for, so a chain can be walked when
    # investigating a replay.
    replaced_by_hash: Mapped[str | None] = mapped_column(String(64))

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")

    def is_active(self, *, now: datetime | None = None) -> bool:
        """True when this token can still be exchanged.

        Python-side, for a row already loaded. Queries filter in SQL instead --
        see `RefreshTokenRepository.get_active`.
        """
        moment = now or datetime.now(tz=self.expires_at.tzinfo)
        return self.revoked_at is None and self.deleted_at is None and self.expires_at > moment

    def revoke(self, reason: str, *, replaced_by_hash: str | None = None) -> None:
        """Mark the token unusable. Caller still has to flush or commit."""
        if self.revoked_at is None:
            self.revoked_at = func.now()
        self.revoked_reason = reason
        if replaced_by_hash is not None:
            self.replaced_by_hash = replaced_by_hash

    def __repr__(self) -> str:
        state = "revoked" if self.revoked_at else "active"
        return f"<RefreshToken(user_id={self.user_id}, session={self.session_id}, {state})>"
