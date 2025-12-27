import logging
import os
from logging.handlers import RotatingFileHandler


LOG_DIR = os.path.join(os.getcwd(), "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")


def setup_logging(level: int = logging.INFO) -> None:
    """Configure application-wide logging once.

    - Creates logs directory if missing
    - Sets root logger level
    - Adds console and rotating file handlers with consistent formatting
    - Sets up domain-specific loggers writing to separate files
    - Avoids duplicate handlers on repeated calls
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    # Ensure idempotent setup
    if getattr(setup_logging, "_configured", False):
        return

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    root.addHandler(ch)

    # General rotating file handler (optional aggregate log)
    fh = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5)
    fh.setLevel(level)
    fh.setFormatter(formatter)
    root.addHandler(fh)

    def setup_category_logger(name: str, filename: str) -> None:
        """Create a named logger that writes only to its own file (no propagation)."""
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = not name.startswith("elastic_search")  # avoid duplicate records to root handlers
        if logger.handlers:
            return
        file_path = os.path.join(LOG_DIR, filename)
        handler = RotatingFileHandler(
            file_path, maxBytes=5 * 1024 * 1024, backupCount=5
        )
        handler.setLevel(level)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Domain-specific loggers
    setup_category_logger("auth", "auth_logs.log")
    setup_category_logger("database", "database.log")
    setup_category_logger("aibot", "aibot.log")
    # Reduce verbosity of noisy third-party loggers if needed
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    setup_logging._configured = True  # type: ignore[attr-defined]
