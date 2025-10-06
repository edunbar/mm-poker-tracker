"""Add live games tables

Revision ID: 20251010_000000
Revises: 20251002_000000
Create Date: 2025-10-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251010_000000'
down_revision: Union[str, Sequence[str], None] = '20251002_000000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add live games tables."""

    # =========================================================================
    # Table 1: live_games
    # =========================================================================
    op.create_table(
        'live_games',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('game_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('join_code', sa.String(length=4), nullable=False),
        sa.Column('status', sa.String(length=20), server_default=sa.text("'active'"), nullable=False),
        sa.Column('small_blind', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('big_blind', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('min_buy_in', sa.Numeric(precision=10, scale=2), server_default=sa.text('10.00'), nullable=False),
        sa.Column('max_buy_in', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('closed_at', sa.TIMESTAMP(timezone=True), nullable=True),

        # Foreign keys
        sa.ForeignKeyConstraint(
            ['game_id'],
            ['games.id'],
            name=op.f('fk_live_games_game_id_games'),
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['created_by_user_id'],
            ['users.id'],
            name=op.f('fk_live_games_created_by_user_id_users'),
            ondelete='SET NULL'
        ),

        # Primary key
        sa.PrimaryKeyConstraint('id', name=op.f('pk_live_games'))
    )

    # Indexes for live_games
    op.create_index('ix_live_games_join_code', 'live_games', ['join_code'], unique=True)
    op.create_index('ix_live_games_game_id', 'live_games', ['game_id'], unique=False)
    op.create_index('ix_live_games_status', 'live_games', ['status'], unique=False)

    # Partial unique index: only one active live game per parent game at a time
    # This prevents creating multiple active live games for the same parent game
    op.execute("""
        CREATE UNIQUE INDEX idx_one_active_live_game_per_game
        ON live_games(game_id)
        WHERE status = 'active';
    """)

    # =========================================================================
    # Table 2: live_game_participants
    # =========================================================================
    op.create_table(
        'live_game_participants',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('live_game_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('joined_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Foreign keys
        sa.ForeignKeyConstraint(
            ['live_game_id'],
            ['live_games.id'],
            name=op.f('fk_live_game_participants_live_game_id_live_games'),
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            name=op.f('fk_live_game_participants_user_id_users'),
            ondelete='CASCADE'
        ),

        # Primary key
        sa.PrimaryKeyConstraint('id', name=op.f('pk_live_game_participants')),

        # Unique constraint: user can only join once per live game
        sa.UniqueConstraint('live_game_id', 'user_id', name='uq_live_game_participants_game_user')
    )

    # Indexes for live_game_participants
    op.create_index('ix_live_game_participants_live_game', 'live_game_participants', ['live_game_id'], unique=False)
    op.create_index('ix_live_game_participants_user', 'live_game_participants', ['user_id'], unique=False)

    # =========================================================================
    # Table 3: live_game_transactions
    # =========================================================================
    op.create_table(
        'live_game_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('live_game_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('participant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_type', sa.String(length=20), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('status', sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('approved_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('original_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('edited_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('edited_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Foreign keys
        sa.ForeignKeyConstraint(
            ['live_game_id'],
            ['live_games.id'],
            name=op.f('fk_live_game_transactions_live_game_id_live_games'),
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['participant_id'],
            ['live_game_participants.id'],
            name=op.f('fk_live_game_transactions_participant_id_live_game_participants'),
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            name=op.f('fk_live_game_transactions_user_id_users'),
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['approved_by_user_id'],
            ['users.id'],
            name=op.f('fk_live_game_transactions_approved_by_user_id_users'),
            ondelete='SET NULL'
        ),
        sa.ForeignKeyConstraint(
            ['edited_by_user_id'],
            ['users.id'],
            name=op.f('fk_live_game_transactions_edited_by_user_id_users'),
            ondelete='SET NULL'
        ),

        # Primary key
        sa.PrimaryKeyConstraint('id', name=op.f('pk_live_game_transactions'))
    )

    # Indexes for live_game_transactions
    op.create_index('ix_live_game_transactions_live_game', 'live_game_transactions', ['live_game_id'], unique=False)
    op.create_index('ix_live_game_transactions_participant', 'live_game_transactions', ['participant_id'], unique=False)
    op.create_index('ix_live_game_transactions_status', 'live_game_transactions', ['live_game_id', 'status'], unique=False)

    # Partial index: pending transactions only (for efficient queries)
    op.execute("""
        CREATE INDEX idx_live_game_transactions_pending
        ON live_game_transactions(live_game_id)
        WHERE status = 'pending';
    """)


def downgrade() -> None:
    """Downgrade schema - remove live games tables."""

    # Drop tables in reverse order (children first, then parents)
    op.drop_index('idx_live_game_transactions_pending', table_name='live_game_transactions')
    op.drop_index('ix_live_game_transactions_status', table_name='live_game_transactions')
    op.drop_index('ix_live_game_transactions_participant', table_name='live_game_transactions')
    op.drop_index('ix_live_game_transactions_live_game', table_name='live_game_transactions')
    op.drop_table('live_game_transactions')

    op.drop_index('ix_live_game_participants_user', table_name='live_game_participants')
    op.drop_index('ix_live_game_participants_live_game', table_name='live_game_participants')
    op.drop_table('live_game_participants')

    op.drop_index('idx_one_active_live_game_per_game', table_name='live_games')
    op.drop_index('ix_live_games_status', table_name='live_games')
    op.drop_index('ix_live_games_game_id', table_name='live_games')
    op.drop_index('ix_live_games_join_code', table_name='live_games')
    op.drop_table('live_games')
