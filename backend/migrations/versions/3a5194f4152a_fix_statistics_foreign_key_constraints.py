"""fix_statistics_foreign_key_constraints

Revision ID: 3a5194f4152a
Revises: b4bd1f7fa9f2
Create Date: 2025-09-25 16:11:52.251543

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a5194f4152a'
down_revision: Union[str, Sequence[str], None] = 'b4bd1f7fa9f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix foreign key constraints on statistics tables.

    Changes player_id foreign keys from CASCADE to RESTRICT on:
    - player_hand_participation
    - player_statistics_cache

    This prevents statistics from being deleted when players are deleted,
    while still allowing deletion when sessions are deleted.
    """

    # Drop existing foreign key constraints for player_id
    op.drop_constraint('fk_player_hand_participation_player_id_players', 'player_hand_participation', type_='foreignkey')
    op.drop_constraint('fk_player_statistics_cache_player_id_players', 'player_statistics_cache', type_='foreignkey')

    # Recreate foreign key constraints with RESTRICT instead of CASCADE
    op.create_foreign_key(
        'fk_player_hand_participation_player_id_players',
        'player_hand_participation',
        'players',
        ['player_id'],
        ['id'],
        ondelete='RESTRICT'
    )

    op.create_foreign_key(
        'fk_player_statistics_cache_player_id_players',
        'player_statistics_cache',
        'players',
        ['player_id'],
        ['id'],
        ondelete='RESTRICT'
    )


def downgrade() -> None:
    """Revert foreign key constraints back to CASCADE."""

    # Drop the RESTRICT constraints
    op.drop_constraint('fk_player_hand_participation_player_id_players', 'player_hand_participation', type_='foreignkey')
    op.drop_constraint('fk_player_statistics_cache_player_id_players', 'player_statistics_cache', type_='foreignkey')

    # Recreate with CASCADE (original behavior)
    op.create_foreign_key(
        'fk_player_hand_participation_player_id_players',
        'player_hand_participation',
        'players',
        ['player_id'],
        ['id'],
        ondelete='CASCADE'
    )

    op.create_foreign_key(
        'fk_player_statistics_cache_player_id_players',
        'player_statistics_cache',
        'players',
        ['player_id'],
        ['id'],
        ondelete='CASCADE'
    )
