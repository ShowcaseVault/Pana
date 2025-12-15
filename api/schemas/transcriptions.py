from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from pydantic.config import ConfigDict
from enum import Enum as PyEnum

from api.config.config import config

class TranscriptionStatus(str, PyEnum):
    pending = "pending"
    completed = "completed"
    failed = "failed"

class TranscriptionCreate(BaseModel):
    recording_id: int
    model_name: str = config.TRANSCRIPTION_MODEL
    status: TranscriptionStatus = TranscriptionStatus.pending.value
    created_at: datetime = datetime.now()

    model_config = ConfigDict(from_attributes=True)

class TranscriptionUpdate(BaseModel):
    text: Optional[str]
    language: Optional[str]
    confidence: Optional[float]
    status: Optional[TranscriptionStatus]
    transcribed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

class TranscriptionResponse(BaseModel):
    id: int
    recording_id: int
    text: Optional[str]
    language: Optional[str]
    confidence: Optional[float]
    model_name: Optional[str]
    status: TranscriptionStatus
    created_at: datetime
    transcribed_at: Optional[datetime]
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)