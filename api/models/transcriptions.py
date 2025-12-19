from sqlalchemy import (
    Column,
    String,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    Float,
    Enum,
    Boolean,
    JSON
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from api.connections.database_creation import Base
from api.schemas.transcriptions import TranscriptionStatus


class Transcription(Base):
    __tablename__ = "transcriptions"

    id = Column(Integer, primary_key=True, index=True)
    recording_id = Column(
        Integer,
        ForeignKey("recordings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    text = Column(Text, nullable=True)
    language = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    model_name = Column(String, nullable=True)
    status = Column(
        Enum(TranscriptionStatus, name="transcription_status"),
        nullable=False,
        default=TranscriptionStatus.pending.value,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    transcribed_at = Column(DateTime(timezone=True), nullable=True)
    words = Column(JSON, nullable=True)
    is_deleted = Column(Boolean, default=False)
    recording = relationship("Recording", back_populates="transcription")
