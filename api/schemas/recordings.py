from datetime import date, datetime

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
    id: int
    user_id: int
    file_path: str
    duration_seconds: int
    recorded_at: datetime
    recording_date: date
    location_text: str | None
    created_at: datetime
    is_deleted: bool
    transcription_status: str | None = None
    transcription_id: int | None = None
    transcription_confidence: float | None = None

    model_config = ConfigDict(from_attributes=True)
