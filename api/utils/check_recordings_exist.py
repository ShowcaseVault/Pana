""" The Util Function to check if the Recordings exist in folder as well as in database """
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.config.config import settings
from api.models.recordings import Recording

recordings_dir = Path(settings.UPLOAD_DIR)

async def check_recordings_exist(db: AsyncSession):
    result = await db.execute(
        select(Recording).where(Recording.is_deleted == False)
    )
    recordings = result.scalars().all()

    db_paths: set[str] = set()
    for recording in recordings:
        if not recording.file_path:
            continue
        rel = str(recording.file_path).lstrip("/\\")
        db_paths.add(str(Path(rel)).replace("\\", "/"))

    fs_paths: set[str] = set()
    if recordings_dir.exists():
        for p in recordings_dir.rglob("*"):
            if p.is_file():
                rel = p.relative_to(recordings_dir)
                fs_paths.add(str(rel).replace("\\", "/"))

    missing_files = sorted(db_paths - fs_paths)
    orphan_files = sorted(fs_paths - db_paths)

    return {
        "total_db": len(db_paths),
        "total_fs": len(fs_paths),
        "missing_files": missing_files,
        "orphan_files": orphan_files,
    }