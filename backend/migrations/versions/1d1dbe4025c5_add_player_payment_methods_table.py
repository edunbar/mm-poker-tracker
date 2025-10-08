"""add_player_payment_methods_table

Revision ID: 1d1dbe4025c5
Revises: 369e3cc49ea3
Create Date: 2025-10-07 16:52:44.634543

NOTE: Payment methods are GLOBAL per player, not per-game.
This means a player's Venmo handle is the same across all games they play in.
No game_id column is needed because these preferences are player-level.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '1d1dbe4025c5'
down_revision: Union[str, Sequence[str], None] = '369e3cc49ea3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create player_payment_methods table for storing player payment preferences."""
    # Create table
    op.create_table(
        'player_payment_methods',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('player_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('players.id', ondelete='CASCADE'), nullable=False),
        sa.Column('payment_method', sa.Text(), nullable=False),
        sa.Column('payment_address', sa.Text(), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()"))
    )

    # Create index on player_id for efficient lookups
    op.create_index('idx_payment_methods_player', 'player_payment_methods', ['player_id'])

    # Create partial unique index to enforce only one primary per player
    # Uses WHERE clause to only index rows where is_primary = true
    op.execute("""
        CREATE UNIQUE INDEX idx_one_primary_per_player
        ON player_payment_methods (player_id)
        WHERE is_primary = true
    """)


def downgrade() -> None:
    """Drop player_payment_methods table."""
    op.drop_index('idx_one_primary_per_player', table_name='player_payment_methods')
    op.drop_index('idx_payment_methods_player', table_name='player_payment_methods')
    op.drop_table('player_payment_methods')
