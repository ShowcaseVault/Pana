"""Transcription task.

The entry point only: it opens a database session and hands off to
`TranscriptionJob`, which holds the work and can be read without Celery in the
picture.
"""

import logging

from api.connections import get_sync_db_session
from api.services.transcription_job import TranscriptionJob
from celery_service.celery_app import celery_app

logger = logging.getLogger("transcription")


@celery_app.task(name="transcribe_audio_task")
def transcribe_audio_task(transcription_id: int) -> None:
    """Transcribe one recording."""
    logger.info("Starting transcription task for %s", transcription_id)

    with get_sync_db_session() as db:
        TranscriptionJob(db).run(transcription_id)
