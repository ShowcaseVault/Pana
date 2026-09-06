"""Database access for diaries."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from api.models.diary import Diary
from api.models.recordings import Recording


class DiaryRepository:
    """Every read and write of the `diaries` table goes through here.

    Also reads the recordings a diary is written from: they are the source
    material for one day's entry, not a separate concern.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_for_date(self, user_id: int, diary_date: date) -> Diary | None:
        """Find the user's diary for one day, if it has been written."""
        stmt = select(Diary).where(
            Diary.user_id == user_id,
            Diary.diary_date == diary_date,
            Diary.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def recordings_for_date(self, user_id: int, diary_date: date) -> list[Recording]:
        """Return the user's recordings for one day, transcriptions loaded.

        Eager-loaded because generating a diary reads each recording's
        transcription, and a lazy load would raise under async SQLAlchemy.
        """
        stmt = (
            select(Recording)
            .where(
                Recording.user_id == user_id,
                Recording.deleted_at.is_(None),
                Recording.recording_date == diary_date,
            )
            .options(joinedload(Recording.transcription))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_for_date(self, user_id: int, diary_date: date) -> bool:
        """Soft-delete the user's diary for one day, if there is one.

        Returns whether a diary was actually removed, so the caller can log the
        cascade without querying again.
        """
        diary = await self.get_for_date(user_id, diary_date)
        if diary is None:
            return False

        diary.soft_delete()
        await self.db.flush()
        return True

    async def upsert(
        self,
        *,
        user_id: int,
        diary_date: date,
        mood: str | None,
        content: str | None,
        actions: list | None,
        recording_file_paths: list[str],
    ) -> Diary:
        """Write the day's diary, replacing an earlier one for the same day.

        Regenerating a diary overwrites rather than adding a second entry:
        one day is one diary, and the newest generation is the current answer.
        """
        diary = await self.get_for_date(user_id, diary_date)

        if diary is None:
            diary = Diary(user_id=user_id, diary_date=diary_date)
            self.db.add(diary)

        diary.mood = mood
        diary.content = content
        diary.actions = actions
        diary.recording_file_paths = recording_file_paths

        await self.db.flush()
        await self.db.refresh(diary)
        return diary
