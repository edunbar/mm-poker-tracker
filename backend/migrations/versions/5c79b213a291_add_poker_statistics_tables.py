"""add_poker_statistics_tables

Revision ID: 5c79b213a291
Revises: b9783b93046c
Create Date: 2025-09-24 16:30:24.451617

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '5c79b213a291'
down_revision: Union[str, Sequence[str], None] = 'b9783b93046c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add poker statistics tables for VPIP, PFR, and Aggression Frequency calculations."""

    # Create player_hand_participation table
    op.create_table(
        'player_hand_participation',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('player_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hand_number', sa.BigInteger(), nullable=False),

        # Hand participation flags
        sa.Column('was_dealt_cards', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('posted_blind', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('posted_sb_amount', sa.BigInteger(), nullable=True),
        sa.Column('posted_bb_amount', sa.BigInteger(), nullable=True),

        # Pre-flop actions for VPIP/PFR
        sa.Column('vpip_eligible', sa.Boolean(), nullable=False, server_default=sa.text('false')),  # Was dealt cards and had opportunity to act
        sa.Column('vpip_action', sa.Boolean(), nullable=False, server_default=sa.text('false')),   # Voluntarily put money in pot pre-flop
        sa.Column('pfr_action', sa.Boolean(), nullable=False, server_default=sa.text('false')),    # Pre-flop raise
        sa.Column('preflop_fold', sa.Boolean(), nullable=False, server_default=sa.text('false')),  # Folded pre-flop

        # Post-flop actions for Aggression Frequency
        sa.Column('postflop_actions', sa.BigInteger(), nullable=False, server_default=sa.text('0')),      # Total post-flop actions taken
        sa.Column('postflop_aggressive', sa.BigInteger(), nullable=False, server_default=sa.text('0')),   # Bets + raises post-flop
        sa.Column('postflop_passive', sa.BigInteger(), nullable=False, server_default=sa.text('0')),      # Calls + checks post-flop

        # Street breakdown for detailed analysis
        sa.Column('flop_actions', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('flop_aggressive', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('turn_actions', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('turn_aggressive', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('river_actions', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('river_aggressive', sa.BigInteger(), nullable=False, server_default=sa.text('0')),

        # Metadata
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),

        # Foreign keys and constraints
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'player_id', 'hand_number', name='uq_player_hand_participation')
    )

    # Add indexes for performance
    op.create_index('ix_player_hand_participation_session', 'player_hand_participation', ['session_id'])
    op.create_index('ix_player_hand_participation_player', 'player_hand_participation', ['player_id'])
    op.create_index('ix_player_hand_participation_session_player', 'player_hand_participation', ['session_id', 'player_id'])

    # Create player_statistics_cache table for aggregated stats
    op.create_table(
        'player_statistics_cache',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('player_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Hand counts for percentage calculations
        sa.Column('hands_dealt', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('vpip_hands', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('pfr_hands', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('postflop_hands', sa.BigInteger(), nullable=False, server_default=sa.text('0')),

        # Action counts for aggression frequency
        sa.Column('postflop_total_actions', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('postflop_aggressive_actions', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('postflop_passive_actions', sa.BigInteger(), nullable=False, server_default=sa.text('0')),

        # Calculated percentages (stored for performance)
        sa.Column('vpip_percentage', sa.Numeric(5, 2), nullable=True),  # e.g., 28.50
        sa.Column('pfr_percentage', sa.Numeric(5, 2), nullable=True),   # e.g., 22.00
        sa.Column('aggression_frequency', sa.Numeric(5, 2), nullable=True),  # e.g., 65.30

        # Street-specific aggression frequencies
        sa.Column('flop_af', sa.Numeric(5, 2), nullable=True),
        sa.Column('turn_af', sa.Numeric(5, 2), nullable=True),
        sa.Column('river_af', sa.Numeric(5, 2), nullable=True),

        # Play style classification
        sa.Column('play_style', sa.Text(), nullable=True),  # 'TAG', 'LAG', 'TP', 'LP'

        # Timestamps
        sa.Column('calculated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),

        # Foreign keys and constraints
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'player_id', name='uq_player_statistics_cache')
    )

    # Add indexes for efficient queries
    op.create_index('ix_player_statistics_session', 'player_statistics_cache', ['session_id'])
    op.create_index('ix_player_statistics_player', 'player_statistics_cache', ['player_id'])
    op.create_index('ix_player_statistics_vpip', 'player_statistics_cache', ['vpip_percentage'])
    op.create_index('ix_player_statistics_pfr', 'player_statistics_cache', ['pfr_percentage'])
    op.create_index('ix_player_statistics_style', 'player_statistics_cache', ['play_style'])


def downgrade() -> None:
    """Remove poker statistics tables."""

    # Drop indexes and tables in reverse order
    op.drop_index('ix_player_statistics_style', table_name='player_statistics_cache')
    op.drop_index('ix_player_statistics_pfr', table_name='player_statistics_cache')
    op.drop_index('ix_player_statistics_vpip', table_name='player_statistics_cache')
    op.drop_index('ix_player_statistics_player', table_name='player_statistics_cache')
    op.drop_index('ix_player_statistics_session', table_name='player_statistics_cache')
    op.drop_table('player_statistics_cache')

    op.drop_index('ix_player_hand_participation_session_player', table_name='player_hand_participation')
    op.drop_index('ix_player_hand_participation_player', table_name='player_hand_participation')
    op.drop_index('ix_player_hand_participation_session', table_name='player_hand_participation')
    op.drop_table('player_hand_participation')
