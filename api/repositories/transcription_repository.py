"""Database access for transcriptions."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.recordings import Recording
from api.models.transcriptions import Transcription
from api.schemas.transcriptions import TranscriptionResponse, TranscriptionStatus


class TranscriptionRepository:
    """Every read and write of the `transcriptions` table goes through here.

    A transcription belongs to a user only through its recording, so every
    query joins `recordings` and filters on the owner there. Without that join
    a transcription id would be enough to read someone else's text.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _owned(self):
        """Base select of live transcriptions joined to their live recording."""
        return (
            select(Transcription)
            .join(Recording, Recording.id == Transcription.recording_id)
            .where(
                Transcription.deleted_at.is_(None),
                Recording.deleted_at.is_(None),
            )
        )

    async def create(
        self,
        *,
        recording_id: int,
        model_name: str | None = None,
        status: TranscriptionStatus | str = TranscriptionStatus.pending,
    ) -> Transcription:
        """Insert a pending transcription for a recording."""
        transcription = Transcription(
            recording_id=recording_id,
            model_name=model_name,
            status=status,
        )
        self.db.add(transcription)
        await self.db.flush()
        await self.db.refresh(transcription)
        return transcription

    async def get_for_user(self, transcription_id: int, user_id: int) -> Transcription | None:
        """Find one live transcription belonging to this user."""
        stmt = self._owned().where(
            Transcription.id == transcription_id,
            Recording.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_recording(self, recording_id: int) -> Transcription | None:
        """Find the live transcription of a recording, if it has one.

        No ownership filter: callers reach this having already loaded the
        recording, which is where ownership was established.
        """
        stmt = select(Transcription).where(
            Transcription.recording_id == recording_id,
            Transcription.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_for_user(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
    ) -> tuple[list[TranscriptionResponse], int]:
        """Return one page of a user's transcriptions, newest first, and the total.

        Rows are converted here: this is the read boundary.
        """
        conditions = [Recording.user_id == user_id]
        if status:
            conditions.append(Transcription.status == status)

        page_stmt = (
            self._owned()
            .where(*conditions)
            .order_by(Transcription.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        count_stmt = (
            select(func.count())
            .select_from(Transcription)
            .join(Recording, Recording.id == Transcription.recording_id)
            .where(
                Transcription.deleted_at.is_(None),
                Recording.deleted_at.is_(None),
                *conditions,
            )
        )

        page = (await self.db.execute(page_stmt)).scalars().all()
        total = (await self.db.execute(count_stmt)).scalar_one()
        return [TranscriptionResponse.model_validate(row) for row in page], total

    async def save(self, transcription: Transcription) -> Transcription:
        """Flush pending changes to a transcription and read it back."""
        await self.db.flush()
        await self.db.refresh(transcription)
        return transcription
