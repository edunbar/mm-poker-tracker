-- Manual SQL migration to create payment ledger tables
-- Run this if alembic migration doesn't work

-- Create payment_transactions table
CREATE TABLE IF NOT EXISTS payment_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id UUID NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    payer_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    recipient_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    amount_cents BIGINT NOT NULL,
    payment_method TEXT,
    payment_date TIMESTAMP WITH TIME ZONE NOT NULL,
    status TEXT NOT NULL DEFAULT 'completed',
    notes TEXT,
    reference_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by TEXT NOT NULL
);

-- Create indexes for payment_transactions
CREATE INDEX IF NOT EXISTS ix_payment_transactions_game_date ON payment_transactions (game_id, payment_date);
CREATE INDEX IF NOT EXISTS ix_payment_transactions_payer ON payment_transactions (payer_id);
CREATE INDEX IF NOT EXISTS ix_payment_transactions_recipient ON payment_transactions (recipient_id);

-- Create payment_balances table
CREATE TABLE IF NOT EXISTS payment_balances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id UUID NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    total_paid BIGINT NOT NULL DEFAULT 0,
    total_received BIGINT NOT NULL DEFAULT 0,
    poker_net_winnings BIGINT NOT NULL DEFAULT 0,
    payment_balance BIGINT NOT NULL DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_payment_balances_game_player UNIQUE (game_id, player_id)
);

-- Create indexes for payment_balances
CREATE INDEX IF NOT EXISTS ix_payment_balances_game ON payment_balances (game_id);
CREATE INDEX IF NOT EXISTS ix_payment_balances_balance ON payment_balances (game_id, payment_balance);

-- Insert migration record (if using alembic)
INSERT INTO alembic_version (version_num) VALUES ('a7f9d2e8b1c4') 
ON CONFLICT (version_num) DO NOTHING;