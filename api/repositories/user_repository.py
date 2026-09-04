"""Database access for users."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.users import User


class UserRepository:
    """Every read and write of the `users` table goes through here."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_google_id(self, google_id: str) -> User | None:
        """Return the live user with this Google subject, or None."""
        stmt = select(User).where(
            User.google_id == google_id,
            User.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create(
        self,
        *,
        google_id: str,
        email: str,
        name: str | None,
        picture: str | None,
    ) -> User:
        """Insert a user and return it with its generated columns populated."""
        user = User(google_id=google_id, email=email, name=name, picture=picture)
        self.db.add(user)
        # Flush rather than commit: the request-scoped session commits once the
        # route returns, so the whole login stays one transaction.
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update_profile(
        self,
        user: User,
        *,
        name: str | None,
        picture: str | None,
    ) -> User:
        """Refresh the fields Google owns on an existing user."""
        user.name = name
        user.picture = picture
        await self.db.flush()
        await self.db.refresh(user)
        return user
