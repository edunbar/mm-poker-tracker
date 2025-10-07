"""add_balance_negative_since_to_payment_balances

Revision ID: 20a695a08906
Revises: b363729b139b
Create Date: 2025-10-06 20:04:40.373682

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20a695a08906'
down_revision: Union[str, Sequence[str], None] = 'b363729b139b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add balance_negative_since column to track when a player's balance became negative.

    CRITICAL: This is payment-grade reliable implementation with:
    - Transaction history reconstruction for backfill
    - Database constraints to enforce invariants
    - Index for performance
    """
    # Step 1: Add column (nullable initially for backfill)
    op.add_column('payment_balances',
        sa.Column('balance_negative_since', sa.TIMESTAMP(timezone=True), nullable=True))

    # Step 2: Backfill using transaction history reconstruction
    # For each negative balance, find the earliest transaction after which balance became negative
    op.execute("""
        UPDATE payment_balances pb
        SET balance_negative_since = (
            WITH player_transactions AS (
                SELECT
                    pt.payment_date,
                    pt.amount_cents,
                    pt.payer_id,
                    pt.recipient_id
                FROM payment_transactions pt
                WHERE pt.game_id = pb.game_id
                  AND (pt.payer_id = pb.player_id OR pt.recipient_id = pb.player_id)
                ORDER BY pt.payment_date ASC
            ),
            balance_timeline AS (
                SELECT
                    payment_date,
                    pb.poker_net_winnings +
                    SUM(CASE
                        WHEN payer_id = pb.player_id THEN amount_cents
                        ELSE 0
                    END) OVER (ORDER BY payment_date) -
                    SUM(CASE
                        WHEN recipient_id = pb.player_id THEN amount_cents
                        ELSE 0
                    END) OVER (ORDER BY payment_date) AS running_balance
                FROM player_transactions
            )
            SELECT MIN(payment_date)
            FROM balance_timeline
            WHERE running_balance < 0
        )
        WHERE pb.payment_balance < 0
    """)

    # Step 3: For negative balances with no transaction history, use NOW()
    # (Conservative estimate - they've been negative since at least now)
    op.execute("""
        UPDATE payment_balances
        SET balance_negative_since = NOW()
        WHERE payment_balance < 0
          AND balance_negative_since IS NULL
    """)

    # Step 4: Add index for performance (partial index on non-NULL values)
    op.create_index(
        'idx_payment_balances_negative_since',
        'payment_balances',
        ['game_id', 'balance_negative_since'],
        postgresql_where=sa.text('balance_negative_since IS NOT NULL')
    )

    # Step 5: Add constraints to enforce data integrity
    # Constraint 1: Negative balance must have timestamp, positive/zero must not
    op.create_check_constraint(
        'chk_balance_negative_since_consistent',
        'payment_balances',
        '(payment_balance < 0 AND balance_negative_since IS NOT NULL) OR '
        '(payment_balance >= 0 AND balance_negative_since IS NULL)'
    )

    # Constraint 2: Timestamp cannot be in the future
    op.create_check_constraint(
        'chk_balance_negative_since_not_future',
        'payment_balances',
        'balance_negative_since IS NULL OR balance_negative_since <= NOW()'
    )


def downgrade() -> None:
    """
    Remove balance_negative_since tracking.

    CRITICAL: This rollback removes constraints, index, and column.
    Code must be rolled back BEFORE running this migration downgrade.
    """
    # Drop constraints first
    op.drop_constraint('chk_balance_negative_since_not_future', 'payment_balances', type_='check')
    op.drop_constraint('chk_balance_negative_since_consistent', 'payment_balances', type_='check')

    # Drop index
    op.drop_index('idx_payment_balances_negative_since', table_name='payment_balances')

    # Drop column
    op.drop_column('payment_balances', 'balance_negative_since')
