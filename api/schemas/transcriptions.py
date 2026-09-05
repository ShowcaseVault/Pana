from datetime import datetime
from enum import Enum as PyEnum

from pydantic import BaseModel
from pydantic.config import ConfigDict

from api.config.config import settings


class TranscriptionStatus(str, PyEnum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class TranscriptionCreate(BaseModel):
    recording_id: int
    model_name: str = settings.TRANSCRIPTION_MODEL
    status: TranscriptionStatus = TranscriptionStatus.pending.value
    created_at: datetime = datetime.now()

    model_config = ConfigDict(from_attributes=True)


class TranscriptionUpdate(BaseModel):
    text: str | None
    language: str | None
    confidence: float | None
    status: TranscriptionStatus | None
    transcribed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class TranscriptionResponse(BaseModel):
    id: int
    recording_id: int
    text: str | None
    language: str | None
    confidence: float | None
    model_name: str | None
    status: TranscriptionStatus
    created_at: datetime
    transcribed_at: datetime | None
    words: list | None = None
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)


class TranscriptionListResponse(BaseModel):
    """One page of transcriptions, with the count of everything that matched."""

    total: int
    data: list[TranscriptionResponse]
