"""Migrate to Clerk authentication

Revision ID: 20251016_000000
Revises: 20251013_000000
Create Date: 2025-10-16 00:00:00.000000

This migration transitions from custom JWT/password authentication to Clerk.
It adds clerk_user_id to the users table and removes password-related fields
and tables that are no longer needed with Clerk's managed authentication.

Changes:
- Add clerk_user_id column to users table
- Drop password_hash and token_version columns from users table
- Drop password_reset_tokens table entirely

Note: clerk_user_id is nullable initially to allow safe migration. In production,
after all users are migrated to Clerk, this can be made NOT NULL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251016_000000'
down_revision: Union[str, Sequence[str], None] = '007a1489ef93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate to Clerk authentication."""

    # 1. Add clerk_user_id column (nullable for safe migration)
    op.add_column('users', sa.Column('clerk_user_id', sa.String(255), nullable=True))

    # 2. Create unique index on clerk_user_id
    op.create_index('ix_users_clerk_user_id', 'users', ['clerk_user_id'], unique=True)

    # 3. Drop password-related columns from users table
    op.drop_column('users', 'password_hash')
    op.drop_column('users', 'token_version')

    # 4. Drop password_reset_tokens table and its indexes
    op.drop_index('ix_password_reset_tokens_expires_at', table_name='password_reset_tokens')
    op.drop_index('ix_password_reset_tokens_user_id', table_name='password_reset_tokens')
    op.drop_index('ix_password_reset_tokens_token_hash', table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')


def downgrade() -> None:
    """Rollback to custom JWT authentication."""

    # 1. Recreate password_reset_tokens table
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('used_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
    )

    # 2. Recreate indexes on password_reset_tokens
    op.create_index('ix_password_reset_tokens_token_hash', 'password_reset_tokens', ['token_hash'])
    op.create_index('ix_password_reset_tokens_user_id', 'password_reset_tokens', ['user_id'])
    op.create_index('ix_password_reset_tokens_expires_at', 'password_reset_tokens', ['expires_at'])

    # 3. Recreate password columns on users table
    # Note: These will be NULL for existing records and need to be populated manually
    op.add_column('users', sa.Column('password_hash', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('token_version', sa.BigInteger, nullable=True, server_default=sa.text("1")))

    # 4. Drop clerk_user_id column and index
    op.drop_index('ix_users_clerk_user_id', table_name='users')
    op.drop_column('users', 'clerk_user_id')
