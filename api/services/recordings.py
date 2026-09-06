"""Recording business logic.

Owns what happens around an audio upload: where the bytes go, the rows that
describe them, and the transcription job that follows.
"""

import logging
from datetime import date, datetime
from pathlib import Path

from fastapi import UploadFile

from api.exceptions import BadRequestError, NotFoundError
from api.models.recordings import Recording
from api.repositories import (
    DiaryRepository,
    RecordingFileRepository,
    RecordingRepository,
    TranscriptionRepository,
)
from api.schemas.recordings import RecordingResponse, RecordingUpdate

logger = logging.getLogger("recordings")

# Browsers are inconsistent about the content type they attach to a recording,
# so the extension is accepted as a second opinion before rejecting an upload.
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".webm", ".flac"}


class RecordingService:
    """Create, read, update, and delete a user's recordings."""

    def __init__(
        self,
        *,
        recordings: RecordingRepository,
        transcriptions: TranscriptionRepository,
        files: RecordingFileRepository,
        diaries: DiaryRepository,
    ) -> None:
        self.recordings = recordings
        self.transcriptions = transcriptions
        self.diaries = diaries
        self.files = files

    async def create(
        self,
        *,
        file: UploadFile,
        user_id: int,
        user_sub: str,
        duration_seconds: int,
        recorded_at: datetime,
        location_text: str | None = None,
    ) -> tuple[RecordingResponse, int | None]:
        """Store an upload, record it, and queue it for transcription.

        Returns the recording and the id of the transcription to enqueue, or
        None when there is nothing to enqueue. The caller owns dispatching the
        job: a Celery worker is another process and must not be handed work
        that this request might still roll back.
        """
        self._require_audio(file)

        file_path = self.files.save(file, user_sub=user_sub, recorded_at=recorded_at)

        recording = await self.recordings.create(
            user_id=user_id,
            file_path=file_path,
            duration_seconds=duration_seconds,
            recorded_at=recorded_at,
            location_text=location_text,
        )

        transcription = await self.transcriptions.create(recording_id=recording.id)
        logger.info(
            "Recording %s created for user %s, transcription %s queued",
            recording.id,
            user_id,
            transcription.id,
        )
        return RecordingResponse.model_validate(recording), transcription.id

    async def get(self, recording_id: int, user_id: int) -> RecordingResponse:
        """Return one of the user's recordings, or raise 404."""
        return RecordingResponse.model_validate(await self._owned_row(recording_id, user_id))

    async def _owned_row(self, recording_id: int, user_id: int) -> Recording:
        """Fetch the ORM row behind a recording the user owns, or raise 404.

        Separate from `get` because updating and deleting need the live row,
        while everything served to a client needs the schema.
        """
        recording = await self.recordings.get_for_user(recording_id, user_id)
        if recording is None:
            raise NotFoundError("Recording not found")
        return recording

    async def list(
        self,
        user_id: int,
        *,
        page: int = 1,
        page_size: int = 100,
        recording_date: date | None = None,
        list_all: bool = False,
    ) -> tuple[list[RecordingResponse], int]:
        """Return a page of the user's recordings and the matching total.

        Without `list_all` and without an explicit date this answers "today",
        which is what the home screen asks for. Paging is expressed as a page
        number here and turned into an offset for the repository, so the route
        and the client speak the same language as the response metadata.
        """
        if not list_all and recording_date is None:
            recording_date = date.today()

        return await self.recordings.list_for_user(
            user_id,
            skip=(page - 1) * page_size,
            limit=page_size,
            recording_date=recording_date,
            list_all=list_all,
        )

    async def update(
        self, recording_id: int, user_id: int, changes: RecordingUpdate
    ) -> RecordingResponse:
        """Apply a partial update to one of the user's recordings."""
        recording = await self._owned_row(recording_id, user_id)

        fields = changes.model_dump(exclude_unset=True)
        for key, value in fields.items():
            setattr(recording, key, value)

        # `recording_date` is derived from `recorded_at`, so moving one moves
        # the other or the date filter would disagree with the timestamp.
        if "recorded_at" in fields:
            recording.recording_date = fields["recorded_at"].date()

        return RecordingResponse.model_validate(await self.recordings.save(recording))

    async def delete(self, recording_id: int, user_id: int) -> None:
        """Soft-delete a recording, its transcription, and any orphaned diary.

        The audio file is left on disk: a soft delete is reversible, and
        removing the bytes would make that a lie.

        A diary is written *from* a day's recordings, so it cannot outlive
        them. When the last recording for a day goes, the day's diary goes with
        it -- otherwise the entry stays readable while claiming to be written
        from nothing, and the calendar keeps marking the day as written.
        Deleting one recording out of several leaves the diary alone: it is now
        slightly out of date, which regenerating fixes, but it is not orphaned.
        """
        recording = await self._owned_row(recording_id, user_id)
        recording_date = recording.recording_date

        transcription = await self.transcriptions.get_by_recording(recording.id)
        if transcription is not None:
            transcription.soft_delete()

        recording.soft_delete()
        await self.recordings.save(recording)

        remaining = await self.recordings.count_for_date(user_id, recording_date)
        if remaining == 0 and await self.diaries.delete_for_date(user_id, recording_date):
            logger.info(
                "Diary for %s removed with the last recording of that day for user %s",
                recording_date,
                user_id,
            )

        logger.info("Recording %s soft-deleted for user %s", recording_id, user_id)

    @staticmethod
    def _require_audio(file: UploadFile) -> None:
        """Reject anything that is not plausibly audio.

        Content type is checked first, with the extension as a fallback:
        browsers and mobile clients disagree about what to send, and a real
        recording arriving as `application/octet-stream` is common enough that
        rejecting on type alone would break uploads.
        """
        content_type = (file.content_type or "").lower()
        if content_type.startswith("audio/"):
            return

        extension = Path(file.filename or "").suffix.lower()
        if extension in ALLOWED_AUDIO_EXTENSIONS:
            return

        raise BadRequestError("Uploaded file must be an audio file")
