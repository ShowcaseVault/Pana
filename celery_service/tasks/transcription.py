import logging
import json
from celery_service.celery_app import celery_app

from api.connections.database_connection import get_sync_db_session
from api.config.redis_client import get_redis_client
from api.models.recordings import Recording
from api.models.transcriptions import Transcription
from api.schemas.transcriptions import TranscriptionStatus
from api.services.transcribe_audio_async import transcribe_audio_file

from api.config.config import settings as CONFIG

logger = logging.getLogger(__name__)

@celery_app.task(name="transcribe_audio_task")
def transcribe_audio_task(transcription_id: int):
    logger.info(f"Starting transcription task for ID: {transcription_id}")
    
    db_gen = get_sync_db_session()
    db = next(db_gen)
    
    try:
        # Fetch Transcription and associated Recording
        transcription = db.query(Transcription).filter(Transcription.id == transcription_id).first()
        if not transcription:
            logger.error(f"Transcription with ID {transcription_id} not found.")
            return

        recording = db.query(Recording).filter(Recording.id == transcription.recording_id).first()
        if not recording:
            logger.error(f"Recording for transcription ID {transcription_id} not found.")
            transcription.status = TranscriptionStatus.failed.value
            db.commit()
            return
            
        # Update status to processing
        transcription.status = TranscriptionStatus.processing.value
        db.commit()

        # Perform Transcription
        logger.info(f"Transcribing file: {recording.file_path}")
        try:
            transcription_data = transcribe_audio_file(recording.file_path)
            
            # Update Transcription record
            transcription.text = transcription_data["text"]
            transcription.language = transcription_data["language"]
            transcription.confidence = transcription_data["confidence"]
            transcription.status = TranscriptionStatus.completed.value
            transcription.transcribed_at = transcription_data["transcribe_time"]
            
            db.commit()
            logger.info(f"Transcription {transcription_id} completed successfully.")

        except Exception as e:
            logger.exception(f"Error during transcription API call: {e}")
            transcription.status = TranscriptionStatus.failed.value
            db.commit()
            raise e
        try:
            redis_client = get_redis_client()
            status_value = (
                transcription.status.value
                if hasattr(transcription.status, "value")
                else transcription.status
            )
            redis_client.publish(
                "transcription_completed",
                json.dumps(
                    {
                        "transcription_id": transcription.id,
                        "recording_id": transcription.recording_id,
                        "status": status_value,
                    }
                ),
            )
        except Exception as e:
            logger.exception(f"Error during Publishing transcription information: {e}")


    except Exception as e:
        logger.exception(f"Unexpected error in task: {e}")
    finally:
        db.close()
