from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from pydantic.config import ConfigDict

class TranscriptionResponse(BaseModel):
    id: int
    recording_id: int
    text: Optional[str]
    language: Optional[str]
    confidence: Optional[float]
    model_name: Optional[str]
    status: str
    created_at: datetime
    transcribed_at: Optional[datetime]
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)