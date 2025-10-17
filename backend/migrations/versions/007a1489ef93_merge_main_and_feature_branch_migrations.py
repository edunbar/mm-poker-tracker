"""merge main and feature branch migrations

Revision ID: 007a1489ef93
Revises: 1d1dbe4025c5, 20251012_120000
Create Date: 2025-10-16 12:19:48.334075

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '007a1489ef93'
down_revision: Union[str, Sequence[str], None] = ('1d1dbe4025c5', '20251012_120000')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
