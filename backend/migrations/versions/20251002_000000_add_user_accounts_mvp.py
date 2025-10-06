"""Add user accounts MVP

Revision ID: 20251002_000000
Revises: e6c53cf9f0ba
Create Date: 2025-10-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251002_000000'
down_revision: Union[str, Sequence[str], None] = 'e6c53cf9f0ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_login_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create unique index on email
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Create poker_identity_claims table
    op.create_table('poker_identity_claims',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('player_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('claimed_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('verification_method', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'player_id', name='uq_identity_user_player'),
        sa.UniqueConstraint('player_id', name='uq_identity_player')
    )

    # Create indexes for poker_identity_claims
    op.create_index('ix_identity_user_player', 'poker_identity_claims', ['user_id', 'player_id'], unique=True)
    op.create_index('ix_identity_player', 'poker_identity_claims', ['player_id'], unique=True)

    # Add columns to games table
    op.add_column('games', sa.Column('owner_user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('games', sa.Column('admin_code_expires_at', sa.TIMESTAMP(timezone=True), nullable=True))

    # Create foreign key constraint for games.owner_user_id
    op.create_foreign_key('fk_games_owner_user', 'games', 'users', ['owner_user_id'], ['id'], ondelete='SET NULL')

    # Create index on games.owner_user_id
    op.create_index('ix_games_owner', 'games', ['owner_user_id'])

    # Add column to audit_log table
    op.add_column('audit_log', sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Create foreign key constraint for audit_log.user_id
    op.create_foreign_key('fk_audit_log_user', 'audit_log', 'users', ['user_id'], ['id'], ondelete='SET NULL')

    # Create index on audit_log.user_id
    op.create_index('ix_audit_log_user', 'audit_log', ['user_id'])


def downgrade() -> None:
    """Downgrade schema."""

    # Drop indexes and columns from audit_log
    op.drop_index('ix_audit_log_user')
    op.drop_constraint('fk_audit_log_user', 'audit_log', type_='foreignkey')
    op.drop_column('audit_log', 'user_id')

    # Drop indexes and columns from games
    op.drop_index('ix_games_owner')
    op.drop_constraint('fk_games_owner_user', 'games', type_='foreignkey')
    op.drop_column('games', 'admin_code_expires_at')
    op.drop_column('games', 'owner_user_id')

    # Drop indexes and table for poker_identity_claims
    op.drop_index('ix_identity_player')
    op.drop_index('ix_identity_user_player')
    op.drop_table('poker_identity_claims')

    # Drop indexes and table for users
    op.drop_index('ix_users_email')
    op.drop_table('users')
