from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func, inspect
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import BaseModel

if TYPE_CHECKING:
    from api.models.transcriptions import Transcription
    from api.models.users import User


class Recording(BaseModel):
    __tablename__ = "recordings"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    file_path: Mapped[str] = mapped_column(Text)
    duration_seconds: Mapped[int | None] = mapped_column()
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recording_date: Mapped[date] = mapped_column(
        Date, index=True, server_default=func.current_date()
    )
    location_text: Mapped[str | None] = mapped_column(String)

    user: Mapped["User"] = relationship(back_populates="recordings")
    # One-to-one
    transcription: Mapped["Transcription | None"] = relationship(
        back_populates="recording",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # The three properties below return None when the relationship was not
    # eager-loaded, so serializing a Recording never triggers a lazy load (which
    # raises under async SQLAlchemy).

    @property
    def transcription_status(self):
        if "transcription" in inspect(self).unloaded:
            return None
        return self.transcription.status.value if self.transcription else None

    @property
    def transcription_id(self):
        if "transcription" in inspect(self).unloaded:
            return None
        return self.transcription.id if self.transcription else None

    @property
    def transcription_confidence(self):
        if "transcription" in inspect(self).unloaded:
            return None
        return self.transcription.confidence if self.transcription else None
