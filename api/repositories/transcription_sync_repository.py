"""Database access for transcriptions from synchronous code.

A separate class from `TranscriptionRepository` because Celery workers run
outside the event loop and use a sync session: the queries are the same shape,
but `await` is not available to spell them.
"""

from sqlalchemy.orm import Session

from api.models.recordings import Recording
from api.models.transcriptions import Transcription
from api.schemas.transcriptions import TranscriptionStatus


class TranscriptionSyncRepository:
    """Reads and writes a transcription while a worker processes it."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, transcription_id: int) -> Transcription | None:
        """Find a transcription by id, deleted or not.

        No soft-delete filter: a job already queued should still record its
        outcome even if the row was deleted while it waited.
        """
        return self.db.get(Transcription, transcription_id)

    def get_recording(self, recording_id: int) -> Recording | None:
        """Find the recording a transcription belongs to."""
        return self.db.get(Recording, recording_id)

    def set_status(self, transcription: Transcription, status: TranscriptionStatus) -> None:
        """Move a transcription to a new status and commit immediately.

        Committed rather than flushed: the status is progress other processes
        watch, and holding it in an open transaction for the length of a slow
        provider call would keep the row locked and the progress invisible.
        """
        transcription.status = status
        self.db.commit()

    def save_result(
        self,
        transcription: Transcription,
        *,
        text: str | None,
        language: str | None,
        confidence: float | None,
        transcribed_at,
        words: list | None,
    ) -> None:
        """Store a finished transcription and mark it completed."""
        transcription.text = text
        transcription.language = language
        transcription.confidence = confidence
        transcription.transcribed_at = transcribed_at
        transcription.words = words
        transcription.status = TranscriptionStatus.completed
        self.db.commit()
