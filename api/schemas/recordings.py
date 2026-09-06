from datetime import datetime

from pydantic import BaseModel
from pydantic.config import ConfigDict


class RecordingCreate(BaseModel):
    duration_seconds: int
    recorded_at: datetime
    location_text: str | None = None


class RecordingUpdate(BaseModel):
    duration_seconds: int | None = None
    recorded_at: datetime | None = None
    location_text: str | None = None


class RecordingResponse(BaseModel):
    """One recording, as a client sees it."""

    id: int

    # The path the audio is fetched by, not a filesystem location: media is
    # served through a route that checks ownership.
    file_path: str
    duration_seconds: int
    recorded_at: datetime
    transcription_status: str | None = None
    transcription_id: int | None = None

    model_config = ConfigDict(from_attributes=True)
