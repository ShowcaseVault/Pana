from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from pydantic.config import ConfigDict


class RecordingCreate(BaseModel):
    duration_seconds: int
    recorded_at: datetime
    location_text: Optional[str] = None


class RecordingUpdate(BaseModel):
    duration_seconds: Optional[int] = None
    recorded_at: Optional[datetime] = None
    location_text: Optional[str] = None


class RecordingResponse(BaseModel):
    id: int
    user_id: int
    file_path: str
    duration_seconds: int
    recorded_at: datetime
    recording_date: datetime
    location_text: Optional[str]
    created_at: datetime
    is_deleted: bool
    transcription_status: Optional[str] = None
    transcription_id: Optional[int] = None
    transcription_confidence: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)