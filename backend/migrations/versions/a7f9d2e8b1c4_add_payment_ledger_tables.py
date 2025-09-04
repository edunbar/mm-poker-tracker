"""Add payment ledger tables

Revision ID: a7f9d2e8b1c4
Revises: 561f32345f38
Create Date: 2025-09-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a7f9d2e8b1c4'
down_revision: Union[str, Sequence[str], None] = '561f32345f38'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # Create payment_transactions table
    op.create_table('payment_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('game_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recipient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount_cents', sa.BigInteger(), nullable=False),
        sa.Column('payment_method', sa.Text(), nullable=True),
        sa.Column('payment_date', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('status', sa.Text(), nullable=False, server_default=sa.text("'completed'")),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('reference_id', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['payer_id'], ['players.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recipient_id'], ['players.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for payment_transactions
    op.create_index('ix_payment_transactions_game_date', 'payment_transactions', ['game_id', 'payment_date'])
    op.create_index('ix_payment_transactions_payer', 'payment_transactions', ['payer_id'])
    op.create_index('ix_payment_transactions_recipient', 'payment_transactions', ['recipient_id'])
    
    # Create payment_balances table
    op.create_table('payment_balances',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('game_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('player_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('total_paid', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('total_received', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('poker_net_winnings', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('payment_balance', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('last_updated', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('game_id', 'player_id', name='uq_payment_balances_game_player')
    )
    
    # Create indexes for payment_balances
    op.create_index('ix_payment_balances_game', 'payment_balances', ['game_id'])
    op.create_index('ix_payment_balances_balance', 'payment_balances', ['game_id', 'payment_balance'])


def downgrade() -> None:
    """Downgrade schema."""
    
    # Drop indexes
    op.drop_index('ix_payment_balances_balance')
    op.drop_index('ix_payment_balances_game')
    op.drop_index('ix_payment_transactions_recipient')
    op.drop_index('ix_payment_transactions_payer')
    op.drop_index('ix_payment_transactions_game_date')
    
    # Drop tables
    op.drop_table('payment_balances')
    op.drop_table('payment_transactions')