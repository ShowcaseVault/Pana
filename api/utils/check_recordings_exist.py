"""Reconcile recording rows against the files on disk.

Answers two questions an operator asks after a bad deploy or a restore: which
rows point at files that are gone, and which files no longer belong to a row.
"""

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from api.config.config import settings
from api.repositories import RecordingRepository


async def check_recordings_exist(db: AsyncSession) -> dict:
    """Compare live recording paths in the database with what is on disk."""
    recordings_dir = Path(settings.RECORDINGS_DIR)

    stored_paths = {
        str(Path(path.lstrip("/\\"))).replace("\\", "/")
        for path in await RecordingRepository(db).all_live_file_paths()
    }

    disk_paths: set[str] = set()
    if recordings_dir.exists():
        for entry in recordings_dir.rglob("*"):
            if entry.is_file():
                disk_paths.add(str(entry.relative_to(recordings_dir)).replace("\\", "/"))

    return {
        "total_db": len(stored_paths),
        "total_fs": len(disk_paths),
        "missing_files": sorted(stored_paths - disk_paths),
        "orphan_files": sorted(disk_paths - stored_paths),
    }
