"""Transcription business logic."""

import logging

from api.exceptions import ConflictError, NotFoundError
from api.models.transcriptions import Transcription
from api.repositories import RecordingRepository, TranscriptionRepository
from api.schemas.transcriptions import TranscriptionUpdate

logger = logging.getLogger("transcriptions")


class TranscriptionService:
    """Read and manage the transcriptions of a user's recordings."""

    def __init__(
        self,
        *,
        transcriptions: TranscriptionRepository,
        recordings: RecordingRepository,
    ) -> None:
        self.transcriptions = transcriptions
        self.recordings = recordings

    async def create(
        self, recording_id: int, user_id: int, *, model_name: str | None = None
    ) -> Transcription:
        """Queue a transcription for one of the user's recordings.

        The recording is looked up through the repository rather than trusted
        from the request, so a recording id belonging to someone else is a 404
        instead of a transcription of their audio.
        """
        recording = await self.recordings.get_for_user(recording_id, user_id)
        if recording is None:
            raise NotFoundError("Recording not found")

        existing = await self.transcriptions.get_by_recording(recording_id)
        if existing is not None:
            # One transcription per recording -- the column is unique, so this
            # is a clearer 409 than the integrity error the insert would raise.
            raise ConflictError("Transcription already exists for this recording")

        return await self.transcriptions.create(recording_id=recording_id, model_name=model_name)

    async def get(self, transcription_id: int, user_id: int) -> Transcription:
        """Return one of the user's transcriptions, or raise 404."""
        transcription = await self.transcriptions.get_for_user(transcription_id, user_id)
        if transcription is None:
            raise NotFoundError("Transcription not found")
        return transcription

    async def list(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
    ) -> tuple[list[Transcription], int]:
        """Return a page of the user's transcriptions and the matching total."""
        return await self.transcriptions.list_for_user(
            user_id, skip=skip, limit=limit, status=status
        )

    async def update(
        self, transcription_id: int, user_id: int, changes: TranscriptionUpdate
    ) -> Transcription:
        """Apply a partial update to one of the user's transcriptions."""
        transcription = await self.get(transcription_id, user_id)

        for key, value in changes.model_dump(exclude_unset=True).items():
            setattr(transcription, key, value)

        return await self.transcriptions.save(transcription)

    async def delete(self, transcription_id: int, user_id: int) -> None:
        """Soft-delete a transcription, leaving its recording alone."""
        transcription = await self.get(transcription_id, user_id)
        transcription.soft_delete()
        await self.transcriptions.save(transcription)
        logger.info("Transcription %s soft-deleted for user %s", transcription_id, user_id)
