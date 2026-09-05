"""The audio files on disk.

The filesystem is external, so it is reached through a repository like any
other outside system: the service decides that a recording is being created,
this decides where the bytes land.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile

from api.config.config import settings
from api.exceptions import AppError

logger = logging.getLogger("recordings")

# Falls back to WAV when an upload arrives with no extension, so a stored path
# always names a decodable file.
DEFAULT_EXTENSION = ".wav"


class RecordingFileRepository:
    """Writes uploaded audio under `RECORDINGS_DIR`."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = Path(base_dir or settings.RECORDINGS_DIR)

    def save(self, file: UploadFile, *, user_sub: str, recorded_at: datetime) -> str:
        """Store an upload and return its path relative to the base directory.

        Files are laid out as `<user>/<date>/<time><ext>`, so one user's
        recordings for one day sit together and a listing is browsable by hand.

        The relative path is what gets stored: an absolute one would break the
        moment the directory moves or the application runs in a container.
        """
        relative_path = self._build_path(file, user_sub=user_sub, recorded_at=recorded_at)
        full_path = self.base_dir / relative_path

        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(full_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except OSError as e:
            logger.exception("Could not write recording to %s", full_path)
            raise AppError("Could not save the uploaded file") from e

        # Posix separators regardless of host: the path is stored in the
        # database and served as a URL, neither of which wants a backslash.
        return relative_path.as_posix()

    def _build_path(self, file: UploadFile, *, user_sub: str, recorded_at: datetime) -> Path:
        extension = Path(file.filename or "").suffix or DEFAULT_EXTENSION
        return (
            Path(user_sub)
            / recorded_at.strftime("%Y-%m-%d")
            / f"{recorded_at.strftime('%H-%M-%S')}{extension}"
        )
