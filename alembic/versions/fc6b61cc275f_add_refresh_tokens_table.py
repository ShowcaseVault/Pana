"""add refresh_tokens table

Refresh tokens become stateful so they can be rotated and revoked: a stateless
one cannot be taken back, and a stolen token would work until it expired. Only
a SHA-256 hash of each token is stored, so a dump of this table yields nothing
usable.

Revision ID: fc6b61cc275f
Revises: 9ee9b259058a
Create Date: 2026-09-04 23:19:34.774134

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc6b61cc275f'
down_revision: Union[str, Sequence[str], None] = '9ee9b259058a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        # Hex-encoded SHA-256: always 64 characters.
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        # Groups one login's rotation chain, so a replay can burn that family
        # without touching the user's other devices.
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        # NULL while the token is usable.
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_reason', sa.String(length=32), nullable=True),
        sa.Column('replaced_by_hash', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_refresh_tokens_id'), 'refresh_tokens', ['id'], unique=False)
    # Unique: the same token can never be recorded twice, which is also what
    # makes replay detection a lookup rather than a scan.
    op.create_index(
        op.f('ix_refresh_tokens_token_hash'), 'refresh_tokens', ['token_hash'], unique=True
    )
    op.create_index(
        op.f('ix_refresh_tokens_session_id'), 'refresh_tokens', ['session_id'], unique=False
    )
    op.create_index(
        op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False
    )
    op.create_index(
        op.f('ix_refresh_tokens_expires_at'), 'refresh_tokens', ['expires_at'], unique=False
    )
    op.create_index(
        op.f('ix_refresh_tokens_deleted_at'), 'refresh_tokens', ['deleted_at'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema.

    Dropping the table logs every session out: with no stored tokens, no
    refresh can be honoured and each client has to sign in again.
    """
    op.drop_index(op.f('ix_refresh_tokens_deleted_at'), table_name='refresh_tokens')
    op.drop_index(op.f('ix_refresh_tokens_expires_at'), table_name='refresh_tokens')
    op.drop_index(op.f('ix_refresh_tokens_user_id'), table_name='refresh_tokens')
    op.drop_index(op.f('ix_refresh_tokens_session_id'), table_name='refresh_tokens')
    op.drop_index(op.f('ix_refresh_tokens_token_hash'), table_name='refresh_tokens')
    op.drop_index(op.f('ix_refresh_tokens_id'), table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
