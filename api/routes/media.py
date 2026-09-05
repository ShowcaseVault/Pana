"""Authenticated access to recording audio files.

Replaces a `StaticFiles` mount. Static serving cannot authorize, and the stored
paths are guessable, so every file is served through an ownership check against
the database instead.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import get_authorized_db_user
from api.connections import get_async_db_session
from api.exceptions import error_docs
from api.models.users import User
from api.repositories import RecordingRepository
from api.services.media import MediaService

router = APIRouter(prefix="/recordings/file", tags=["Media"])


def get_media_service(
    db: AsyncSession = Depends(get_async_db_session),
) -> MediaService:
    """Build the media service with the repository it needs."""
    return MediaService(RecordingRepository(db))


@router.get("/{file_path:path}", responses=error_docs(401, 404))
async def get_recording_file(
    file_path: str,
    user: User = Depends(get_authorized_db_user),
    service: MediaService = Depends(get_media_service),
) -> FileResponse:
    """Stream a recording the caller owns."""
    full_path = await service.resolve(file_path, user.id)
    return FileResponse(full_path, filename=full_path.name)
