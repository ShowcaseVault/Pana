"""Running one transcription job.

The work a Celery task does, kept out of the task itself so it can be read and
tested without a worker. The task stays a thin entry point: open a session,
call this, done.
"""

import asyncio
import logging

from sqlalchemy.orm import Session

from api.models.transcriptions import Transcription
from api.repositories import (
    TranscriptionSyncRepository,
    publish_transcription_completed,
)
from api.schemas.transcriptions import TranscriptionStatus
from api.services.transcribe_audio_async import transcribe_audio_file

logger = logging.getLogger("transcription")


class TranscriptionJob:
    """Transcribes one recording and records how it went."""

    def __init__(self, db: Session) -> None:
        self.transcriptions = TranscriptionSyncRepository(db)

    def run(self, transcription_id: int) -> None:
        """Transcribe a recording, storing the outcome either way.

        Never raises. A failure is a state the row records and the client is
        told about, not an exception for Celery to retry blindly -- a bad audio
        file would fail identically on every attempt.
        """
        transcription = self.transcriptions.get(transcription_id)
        if transcription is None:
            logger.error("Transcription %s not found", transcription_id)
            return

        recording = self.transcriptions.get_recording(transcription.recording_id)
        if recording is None:
            logger.error("Recording for transcription %s not found", transcription_id)
            self._fail(transcription, recording_user_id=None)
            return

        self.transcriptions.set_status(transcription, TranscriptionStatus.processing)

        try:
            result = asyncio.run(transcribe_audio_file(recording.file_path))
        except Exception:
            logger.exception("Transcription %s failed", transcription_id)
            self._fail(transcription, recording_user_id=recording.user_id)
            return

        self.transcriptions.save_result(
            transcription,
            text=result["text"],
            language=result["language"],
            confidence=result["confidence"],
            transcribed_at=result["transcribe_time"],
            words=result["words"],
        )
        logger.info("Transcription %s completed", transcription_id)
        self._announce(transcription, recording.user_id)

    def _fail(self, transcription: Transcription, *, recording_user_id: int | None) -> None:
        """Mark a transcription failed and tell the owner it will not arrive.

        The client is waiting on the event stream, so a failure has to be
        announced too -- otherwise a broken job looks the same as a slow one
        and the listener waits forever.
        """
        self.transcriptions.set_status(transcription, TranscriptionStatus.failed)

        if recording_user_id is not None:
            self._announce(transcription, recording_user_id)

    @staticmethod
    def _announce(transcription: Transcription, user_id: int) -> None:
        publish_transcription_completed(
            user_id,
            transcription_id=transcription.id,
            recording_id=transcription.recording_id,
            status=transcription.status.value,
        )
