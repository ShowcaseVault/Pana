"""Authenticated access to recording audio files.

Replaces a `StaticFiles` mount. Static serving cannot authorize, and the stored
paths are guessable -- `<google_sub>/<date>/<HH-MM-SS>.wav` -- so anyone holding
a user's Google subject could enumerate that user's recordings by trying dates
and times. Every file is now served through an ownership check against the
database instead.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import get_authorized_db_user
from api.config.config import settings
from api.connections import get_async_db_session
from api.exceptions import NotFoundError, error_docs
from api.models.recordings import Recording

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recordings/file", tags=["Media"])


def _resolve_within_recordings(file_path: str) -> Path:
    """Resolve `file_path` inside RECORDINGS_DIR, refusing anything that escapes it.

    Checked after resolution, so `..` segments and symlinks are both caught.
    """
    root = Path(settings.RECORDINGS_DIR).resolve()
    candidate = (root / file_path).resolve()

    if candidate != root and root not in candidate.parents:
        raise NotFoundError("Recording not found")

    return candidate


@router.get("/{file_path:path}", responses=error_docs(401, 404))
async def get_recording_file(
    file_path: str,
    user=Depends(get_authorized_db_user),
    db: AsyncSession = Depends(get_async_db_session),
) -> FileResponse:
    """Stream a recording the caller owns.

    A file belonging to someone else returns 404 rather than 403: a 403 would
    confirm the recording exists, which is the enumeration this route closes.
    """
    normalized = file_path.lstrip("/\\").replace("\\", "/")

    result = await db.execute(
        select(Recording).where(
            Recording.file_path == normalized,
            Recording.user_id == user.id,
            Recording.deleted_at.is_(None),
        )
    )
    recording = result.scalars().first()

    if recording is None:
        logger.warning("Denied recording access for user %s: %s", user.id, normalized)
        raise NotFoundError("Recording not found")

    full_path = _resolve_within_recordings(normalized)
    if not full_path.is_file():
        logger.error("Recording row %s has no file on disk: %s", recording.id, normalized)
        raise NotFoundError("Recording not found")

    return FileResponse(full_path, filename=full_path.name)
