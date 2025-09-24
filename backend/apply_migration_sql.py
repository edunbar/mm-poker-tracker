import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

sql = """
-- Create poker_events table
CREATE TABLE IF NOT EXISTS poker_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    hand_number BIGINT,
    event_type TEXT NOT NULL,
    player_id UUID REFERENCES players(id) ON DELETE SET NULL,
    player_name TEXT,
    amount BIGINT,
    cards TEXT,
    event_timestamp TIMESTAMP WITH TIME ZONE,
    order_number BIGINT,
    raw_entry TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_poker_events_session_id ON poker_events(session_id);
CREATE INDEX IF NOT EXISTS ix_poker_events_hand_number ON poker_events(session_id, hand_number);
CREATE INDEX IF NOT EXISTS ix_poker_events_player_id ON poker_events(player_id);

-- Create hand_summaries table
CREATE TABLE IF NOT EXISTS hand_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    hand_number BIGINT NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE,
    ended_at TIMESTAMP WITH TIME ZONE,
    pot_size BIGINT,
    winner_id UUID REFERENCES players(id) ON DELETE SET NULL,
    winner_name TEXT,
    board_cards TEXT,
    num_players INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_hand_summaries_session_hand UNIQUE (session_id, hand_number)
);

CREATE INDEX IF NOT EXISTS ix_hand_summaries_session_id ON hand_summaries(session_id);
CREATE INDEX IF NOT EXISTS ix_hand_summaries_winner_id ON hand_summaries(winner_id);

-- Add ff8220ff746c (ledger_csv) if not exists
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS ledger_csv_content TEXT;

-- Update alembic_version
DELETE FROM alembic_version WHERE version_num IN ('ff8220ff746c', 'b9783b93046c', '50fa7cebf354');
INSERT INTO alembic_version (version_num) VALUES ('b9783b93046c');
"""

cur.execute(sql)
conn.commit()
cur.close()
conn.close()

print("✅ Migration applied successfully!")
print("Tables created: poker_events, hand_summaries")
print("Alembic version updated to: b9783b93046c")