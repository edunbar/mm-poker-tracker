"""add_alert_settings_to_games

Revision ID: b363729b139b
Revises: e6c53cf9f0ba
Create Date: 2025-10-06 17:50:09.889880

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b363729b139b'
down_revision: Union[str, Sequence[str], None] = 'e6c53cf9f0ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('games', sa.Column('alert_settings',
        postgresql.JSONB(astext_type=sa.Text()),
        server_default=sa.text("'{}'::jsonb"),
        nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('games', 'alert_settings')
