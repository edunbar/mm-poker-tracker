"""Add token_version to users for session invalidation

Revision ID: 20251012_000000
Revises: 20251010_000000
Create Date: 2025-10-12 00:00:00.000000

This migration adds a token_version field to the users table to enable
session invalidation on password changes. When a user resets their password,
this version is incremented, invalidating all existing JWT tokens.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20251012_000000'
down_revision: Union[str, Sequence[str], None] = '20251010_000000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add token_version column to users table."""

    # Add token_version column with default value of 1
    op.add_column('users',
        sa.Column('token_version', sa.BigInteger(), nullable=False, server_default=sa.text('1'))
    )

    # Backfill existing users with token_version = 1
    # (server_default handles this automatically, but being explicit for clarity)
    op.execute("UPDATE users SET token_version = 1 WHERE token_version IS NULL")


def downgrade() -> None:
    """Remove token_version column from users table."""

    # Drop the token_version column
    op.drop_column('users', 'token_version')
