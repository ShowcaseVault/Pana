"""Database access for recordings."""

from datetime import date

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from api.models.recordings import Recording


class RecordingRepository:
    """Every read and write of the `recordings` table goes through here."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        *,
        user_id: int,
        file_path: str,
        duration_seconds: int,
        recorded_at,
        location_text: str | None,
    ) -> Recording:
        """Insert a recording row for a file already written to disk."""
        recording = Recording(
            user_id=user_id,
            file_path=file_path,
            duration_seconds=duration_seconds,
            recorded_at=recorded_at,
            recording_date=recorded_at.date(),
            location_text=location_text,
        )
        self.db.add(recording)
        await self.db.flush()
        await self.db.refresh(recording)
        return recording

    async def get_for_user(self, recording_id: int, user_id: int) -> Recording | None:
        """Find one live recording belonging to this user.

        Ownership is part of the query, not a check afterwards: a recording
        belonging to someone else is simply not found, so it cannot leak
        through a forgotten comparison.

        The transcription is eager-loaded because `RecordingResponse` reads it,
        and a lazy load would raise under async SQLAlchemy.
        """
        stmt = (
            select(Recording)
            .where(
                Recording.id == recording_id,
                Recording.user_id == user_id,
                Recording.deleted_at.is_(None),
            )
            .options(joinedload(Recording.transcription))
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_for_user(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 100,
        recording_date: date | None = None,
        list_all: bool = False,
    ) -> tuple[list[Recording], int]:
        """Return one page of a user's recordings, newest first, and the total.

        The total counts every row matching the filter, not just this page, so
        a client can show how many there are without fetching them all.
        """
        conditions = [
            Recording.user_id == user_id,
            Recording.deleted_at.is_(None),
        ]
        if not list_all:
            conditions.append(func.date(Recording.recorded_at) == recording_date)

        page_stmt = (
            select(Recording)
            .where(*conditions)
            .order_by(desc(Recording.recorded_at))
            .options(joinedload(Recording.transcription))
            .offset(skip)
            .limit(limit)
        )
        count_stmt = select(func.count()).select_from(Recording).where(*conditions)

        page = (await self.db.execute(page_stmt)).scalars().all()
        total = (await self.db.execute(count_stmt)).scalar_one()
        return list(page), total

    async def save(self, recording: Recording) -> Recording:
        """Flush pending changes to a recording and read it back."""
        await self.db.flush()
        await self.db.refresh(recording)
        return recording
