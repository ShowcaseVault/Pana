from sqlalchemy import (
    Column,
    Integer,
    Text,
    DateTime,
    Date,
    ForeignKey,
    Boolean,
    JSON
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from api.connections.database_creation import Base
from datetime import datetime


class Diary(Base):
    __tablename__ = "diaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    diary_date = Column(Date,nullable=False, index=True, server_default=func.current_date())
    mood = Column(Text)
    content = Column(Text)
    actions = Column(JSON)
    recording_file_paths = Column(JSON)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    is_deleted = Column(Boolean, default=False)
