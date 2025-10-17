"""add player_id to live_game_participants

Revision ID: 20251012_120000
Revises: 20251013_000000
Create Date: 2025-10-12 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251012_120000'
down_revision = '20251013_000000'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add player_id column to live_game_participants table.

    This enables linking live game participants to their poker player identities,
    supporting the player identity claiming system for live games.

    Migration Safety Notes:
    - player_id is nullable to support existing participants without claims
    - No breaking changes to existing data
    - No immediate backfill required
    - Safe to deploy without data migration
    """
    # Add player_id column (nullable for backwards compatibility)
    op.add_column('live_game_participants',
        sa.Column('player_id', postgresql.UUID(as_uuid=True), nullable=True)
    )

    # Add foreign key constraint with CASCADE delete
    # When a player is deleted, the participant link is also deleted
    op.create_foreign_key(
        'fk_live_game_participants_player_id',
        'live_game_participants', 'players',
        ['player_id'], ['id'],
        ondelete='CASCADE'
    )

    # Add index for query performance
    # This will be used frequently when looking up participants by player_id
    op.create_index(
        'ix_live_game_participants_player_id',
        'live_game_participants',
        ['player_id']
    )


def downgrade():
    """
    Remove player_id column and related constraints.
    """
    # Drop index first
    op.drop_index('ix_live_game_participants_player_id', table_name='live_game_participants')

    # Drop foreign key constraint
    op.drop_constraint('fk_live_game_participants_player_id', 'live_game_participants', type_='foreignkey')

    # Drop column
    op.drop_column('live_game_participants', 'player_id')
