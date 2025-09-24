"""add_poker_hand_log_tables

Revision ID: b9783b93046c
Revises: ff8220ff746c
Create Date: 2025-09-23 20:55:15.231504

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b9783b93046c'
down_revision: Union[str, Sequence[str], None] = 'ff8220ff746c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'poker_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hand_number', sa.BigInteger(), nullable=True),
        sa.Column('event_type', sa.Text(), nullable=False),
        sa.Column('player_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('player_name', sa.Text(), nullable=True),
        sa.Column('amount', sa.BigInteger(), nullable=True),
        sa.Column('cards', sa.Text(), nullable=True),
        sa.Column('event_timestamp', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('order_number', sa.BigInteger(), nullable=True),
        sa.Column('raw_entry', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_poker_events_session_id', 'poker_events', ['session_id'])
    op.create_index('ix_poker_events_hand_number', 'poker_events', ['session_id', 'hand_number'])
    op.create_index('ix_poker_events_player_id', 'poker_events', ['player_id'])

    op.create_table(
        'hand_summaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hand_number', sa.BigInteger(), nullable=False),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('ended_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('pot_size', sa.BigInteger(), nullable=True),
        sa.Column('winner_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('winner_name', sa.Text(), nullable=True),
        sa.Column('board_cards', sa.Text(), nullable=True),
        sa.Column('num_players', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['winner_id'], ['players.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'hand_number', name='uq_hand_summaries_session_hand')
    )
    op.create_index('ix_hand_summaries_session_id', 'hand_summaries', ['session_id'])
    op.create_index('ix_hand_summaries_winner_id', 'hand_summaries', ['winner_id'])


def downgrade() -> None:
    op.drop_index('ix_hand_summaries_winner_id', table_name='hand_summaries')
    op.drop_index('ix_hand_summaries_session_id', table_name='hand_summaries')
    op.drop_table('hand_summaries')
    op.drop_index('ix_poker_events_player_id', table_name='poker_events')
    op.drop_index('ix_poker_events_hand_number', table_name='poker_events')
    op.drop_index('ix_poker_events_session_id', table_name='poker_events')
    op.drop_table('poker_events')