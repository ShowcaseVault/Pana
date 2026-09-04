from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import BaseModel
from api.schemas.transcriptions import TranscriptionStatus

if TYPE_CHECKING:
    from api.models.recordings import Recording


class Transcription(BaseModel):
    __tablename__ = "transcriptions"

    recording_id: Mapped[int] = mapped_column(
        ForeignKey("recordings.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    text: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String)
    confidence: Mapped[float | None] = mapped_column()
    model_name: Mapped[str | None] = mapped_column(String)
    status: Mapped[TranscriptionStatus] = mapped_column(
        Enum(TranscriptionStatus, name="transcription_status"),
        default=TranscriptionStatus.pending,
    )
    transcribed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    words: Mapped[list | None] = mapped_column(JSON)

    recording: Mapped["Recording"] = relationship(back_populates="transcription")
