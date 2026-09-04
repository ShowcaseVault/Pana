from celery import Celery
from celery.signals import setup_logging as celery_setup_logging

from api.config.config import settings
from api.utils.logging_config import setup_logging

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
    # Celery replaces the root logger's handlers on worker start unless told
    # not to. Left on, every task log line goes to the worker's stderr only and
    # never reaches the rotating files.
    worker_hijack_root_logger=False,
)


@celery_setup_logging.connect
def configure_worker_logging(**_kwargs) -> None:
    """Give the worker the same handlers as the API.

    Connecting to this signal at all suppresses Celery's own logging setup, so
    the configuration below is the only one in effect.
    """
    setup_logging()
