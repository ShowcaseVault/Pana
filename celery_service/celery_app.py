from celery import Celery

from api.config.config import settings

celery_app = Celery(
    "worker",
    broker=settings.REDIS_BROKER_URL,
    backend=settings.REDIS_RESULT_BACKEND,
    include=["celery_service.tasks.transcription"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue="default",
)
