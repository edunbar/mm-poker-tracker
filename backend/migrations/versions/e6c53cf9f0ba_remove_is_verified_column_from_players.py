"""remove_is_verified_column_from_players

Revision ID: e6c53cf9f0ba
Revises: 3a5194f4152a
Create Date: 2025-09-30 20:02:33.440209

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6c53cf9f0ba'
down_revision: Union[str, Sequence[str], None] = '3a5194f4152a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('players', 'is_verified')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('players', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('FALSE')))
