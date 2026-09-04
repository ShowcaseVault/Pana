from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Date, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import BaseModel

if TYPE_CHECKING:
    from api.models.users import User


class Diary(BaseModel):
    __tablename__ = "diaries"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    diary_date: Mapped[date] = mapped_column(Date, index=True, server_default=func.current_date())
    mood: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text)
    actions: Mapped[list | None] = mapped_column(JSON)
    recording_file_paths: Mapped[list | None] = mapped_column(JSON)

    user: Mapped["User"] = relationship(back_populates="diaries")
