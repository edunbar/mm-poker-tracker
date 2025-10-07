"""remove_balance_negative_since_not_future_constraint

Revision ID: 369e3cc49ea3
Revises: 20a695a08906
Create Date: 2025-10-06 20:54:30.616350

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '369e3cc49ea3'
down_revision: Union[str, Sequence[str], None] = '20a695a08906'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove chk_balance_negative_since_not_future constraint.

    This constraint causes false positives due to microsecond-level race conditions
    between Python's datetime.now() and PostgreSQL's NOW() evaluation.

    The critical invariant (negative balances must have timestamps) is already
    enforced by chk_balance_negative_since_consistent.
    """
    op.drop_constraint('chk_balance_negative_since_not_future', 'payment_balances', type_='check')


def downgrade() -> None:
    """Recreate chk_balance_negative_since_not_future constraint."""
    op.create_check_constraint(
        'chk_balance_negative_since_not_future',
        'payment_balances',
        'balance_negative_since IS NULL OR balance_negative_since <= NOW()'
    )
