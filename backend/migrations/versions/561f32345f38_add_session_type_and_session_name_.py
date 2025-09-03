"""Add session_type and session_name fields to sessions table

Revision ID: 561f32345f38
Revises: 4a6d21595acf
Create Date: 2025-09-02 15:10:36.805107

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '561f32345f38'
down_revision: Union[str, Sequence[str], None] = '4a6d21595acf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add session_type column with default value 'pokernow'
    op.add_column('sessions', sa.Column('session_type', sa.Text(), nullable=False, server_default=sa.text("'pokernow'")))
    
    # Add session_name column for human-readable names (nullable)
    op.add_column('sessions', sa.Column('session_name', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove the new columns
    op.drop_column('sessions', 'session_name')
    op.drop_column('sessions', 'session_type')
