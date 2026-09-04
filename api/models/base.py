"""Shared declarative base for every model.

`BaseModel` carries the four columns every table needs -- surrogate key,
insert time, update time, and soft-delete time -- so the concrete models hold
only the fields that describe their own domain.

Columns are declared with `Mapped`/`mapped_column` (SQLAlchemy 2.0 style): the
Python type is read off the annotation, so `Mapped[int]` is NOT NULL and
`Mapped[str | None]` is nullable without repeating `nullable=` on each column,
and type checkers see the real attribute types instead of `Column`.
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base. Holds the shared metadata, no columns of its own."""


class BaseModel(Base):
    """Abstract parent for every table.

    Timestamps are written by the database (`server_default`/`onupdate`), not by
    the application, so a row inserted by a migration or by psql gets the same
    values as one inserted through the ORM.
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    # Soft delete: NULL means live. A timestamp records when the row was
    # deleted, which a boolean flag cannot.
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    @property
    def is_deleted(self) -> bool:
        """True when the row has been soft-deleted.

        Read-only and Python-side. Filter queries with
        `Model.deleted_at.is_(None)`, which emits SQL; this property does not.
        """
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark the row deleted. Caller still has to flush or commit."""
        self.deleted_at = datetime.now()
