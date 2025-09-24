"""add_ledger_csv_content_to_sessions

Revision ID: ff8220ff746c
Revises: ee23b4b91362
Create Date: 2025-09-23 19:15:32.185181

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff8220ff746c'
down_revision: Union[str, Sequence[str], None] = 'ee23b4b91362'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('sessions', sa.Column('ledger_csv_content', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('sessions', 'ledger_csv_content')
