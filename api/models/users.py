from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import BaseModel

if TYPE_CHECKING:
    from api.models.diary import Diary
    from api.models.recordings import Recording
    from api.models.refresh_tokens import RefreshToken


class User(BaseModel):
    __tablename__ = "users"

    google_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String)
    picture: Mapped[str | None] = mapped_column(String)

    recordings: Mapped[list["Recording"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    diaries: Mapped[list["Diary"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<User(email={self.email}, google_id={self.google_id})>"
