"""soft delete orphaned diaries

A diary is written from a day's recordings, so it cannot outlive them.
Deleting the last recording of a day now removes that day's diary with it, but
rows written before that cascade existed are still in the table: readable,
marked as written in the calendar, and sourced from nothing.

This clears them once. It touches only diaries whose day has no live recordings
left, so a diary that still has audio behind it is untouched.

Revision ID: 3084b5cb4b5a
Revises: fc6b61cc275f
Create Date: 2026-09-06

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "3084b5cb4b5a"
down_revision: Union[str, Sequence[str], None] = "fc6b61cc275f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Soft-delete every diary whose day holds no live recordings."""
    op.execute(
        sa.text(
            """
            UPDATE diaries
            SET deleted_at = NOW()
            WHERE deleted_at IS NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM recordings
                  WHERE recordings.user_id = diaries.user_id
                    AND recordings.recording_date = diaries.diary_date
                    AND recordings.deleted_at IS NULL
              )
            """
        )
    )


def downgrade() -> None:
    """Not reversible.

    The rows this removed are indistinguishable from diaries deleted for any
    other reason once the timestamp is set, so restoring them would also
    restore entries the user deleted deliberately.
    """
    pass
