"""Serving recording audio files.

Two things have to be true before bytes go out: the caller owns the recording,
and the path resolves inside the recordings directory. The first is a database
question, the second a filesystem one, and both are answered here.
"""

import logging
from pathlib import Path

from api.config.config import settings
from api.exceptions import NotFoundError
from api.repositories import RecordingRepository

logger = logging.getLogger("media")


class MediaService:
    """Resolves a stored path to a file the caller is allowed to read."""

    def __init__(self, recordings: RecordingRepository) -> None:
        self.recordings = recordings

    async def resolve(self, file_path: str, user_id: int) -> Path:
        """Return the file for a path the user owns.

        Everything that fails raises the same 404. A 403 would confirm the
        recording exists, and the stored paths are guessable --
        `<google_sub>/<date>/<HH-MM-SS>.wav` -- so telling the difference is
        exactly the enumeration this route exists to prevent.
        """
        normalized = file_path.lstrip("/\\").replace("\\", "/")

        recording = await self.recordings.get_by_path(normalized, user_id)
        if recording is None:
            logger.warning("Denied recording access for user %s: %s", user_id, normalized)
            raise NotFoundError("Recording not found")

        full_path = self._resolve_within_root(normalized)
        if not full_path.is_file():
            logger.error("Recording %s has no file on disk: %s", recording.id, normalized)
            raise NotFoundError("Recording not found")

        return full_path

    @staticmethod
    def _resolve_within_root(file_path: str) -> Path:
        """Resolve a path inside the recordings directory, refusing escapes.

        Checked after resolution rather than by inspecting the string, so `..`
        segments and symlinks pointing outside are both caught.
        """
        root = Path(settings.RECORDINGS_DIR).resolve()
        candidate = (root / file_path).resolve()

        if candidate != root and root not in candidate.parents:
            raise NotFoundError("Recording not found")

        return candidate
