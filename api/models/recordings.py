import uuid
from sqlalchemy import (
    Column,
    String,
    Integer,
    Text,
    Date,
    DateTime,
    ForeignKey,
    Float,
    Enum,
    Boolean
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from api.connections.database_creation import Base

class Recording(Base):
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path = Column(Text, nullable=False)
    duration_seconds = Column(Integer)
    recorded_at = Column(DateTime(timezone=True), nullable=False)
    recording_date = Column(Date, nullable=False, index=True)
    location_text = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    is_deleted = Column(Boolean, default=False)
    # One-to-one relationship
    transcription = relationship(
        "Transcription",
        back_populates="recording",
        uselist=False,
        cascade="all, delete-orphan",
    )
