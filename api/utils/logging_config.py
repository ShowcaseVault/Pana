"""Application logging.

One rotating file per concern, plus a console stream. Rotation is bounded:
each file rolls at `LOG_MAX_BYTES` and keeps `LOG_BACKUP_COUNT` older copies,
so total disk use per logger is capped at (count + 1) * max_bytes and never
grows without limit on a long-running worker.

`setup_logging()` is called by both the API factory and the Celery worker
startup hook, and is idempotent -- calling it twice does not double every
record.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from api.config.config import settings

CATEGORY_LOGGERS: dict[str, str] = {
    "database": "database.log",
    "api.errors": "errors.log",
    "api.request": "access.log",
    "celery_service": "celery.log",
}

_configured = False


def _log_dir() -> str:
    """Absolute path of the log directory, created if missing."""
    path = settings.LOG_DIR
    if not os.path.isabs(path):
        path = os.path.join(os.getcwd(), path)
    os.makedirs(path, exist_ok=True)
    return path


def _rotating_handler(path: str, formatter: logging.Formatter) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        path,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    return handler


def setup_logging(level: int | str | None = None) -> None:
    """Configure root and per-category logging. Safe to call more than once."""
    global _configured
    if _configured:
        return

    resolved = level if level is not None else settings.LOG_LEVEL
    if isinstance(resolved, str):
        resolved = logging.getLevelNamesMapping().get(resolved.upper(), logging.INFO)

    log_dir = _log_dir()

    # The file keeps the full record: a line read weeks later has no
    # surrounding context, so it carries the date and the logger name.
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # The console is read live, so it drops what the reader already knows. The
    # date is today and the logger name is usually guessable from the message;
    # spending half the terminal width on both leaves no room for the part that
    # matters.
    console_formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(resolved)

    console = logging.StreamHandler()
    console.setFormatter(console_formatter)
    root.addHandler(console)
    root.addHandler(_rotating_handler(os.path.join(log_dir, "app.log"), formatter))

    # Category loggers keep propagate=True, so their records reach app.log as
    # well as their own file. app.log stays the single place to read a request
    # end to end; the per-category file is for reading one concern in isolation.
    for name, filename in CATEGORY_LOGGERS.items():
        logger = logging.getLogger(name)
        logger.setLevel(resolved)
        if not logger.handlers:
            logger.addHandler(_rotating_handler(os.path.join(log_dir, filename), formatter))

    # Third-party loggers that are noisy at INFO.
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("multipart").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)

    # Uvicorn's own access log would duplicate RequestLoggingMiddleware, in a
    # format that cannot skip the event stream or flag a slow request. The
    # middleware is the one that knows what is worth printing, so this is the
    # line that goes.
    logging.getLogger("uvicorn.access").disabled = True

    _configured = True
