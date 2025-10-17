"""Add password_reset_tokens table for password reset flow

Revision ID: 20251013_000000
Revises: 20251012_000000
Create Date: 2025-10-13 00:00:00.000000

This migration adds a password_reset_tokens table to support secure
password reset functionality. Users can request a password reset via email,
receive a time-limited token, and use it to set a new password.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251013_000000'
down_revision: Union[str, Sequence[str], None] = '20251012_000000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add password_reset_tokens table."""

    op.create_table(
        'password_reset_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False),  # SHA256 hash = 64 hex chars
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('used_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),  # IPv6 max length
    )

    # Index on token_hash for fast lookups
    op.create_index('ix_password_reset_tokens_token_hash', 'password_reset_tokens', ['token_hash'])

    # Index on user_id for cleanup queries
    op.create_index('ix_password_reset_tokens_user_id', 'password_reset_tokens', ['user_id'])

    # Index on expires_at for cleanup of old tokens
    op.create_index('ix_password_reset_tokens_expires_at', 'password_reset_tokens', ['expires_at'])


def downgrade() -> None:
    """Remove password_reset_tokens table."""

    op.drop_index('ix_password_reset_tokens_expires_at', table_name='password_reset_tokens')
    op.drop_index('ix_password_reset_tokens_user_id', table_name='password_reset_tokens')
    op.drop_index('ix_password_reset_tokens_token_hash', table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
