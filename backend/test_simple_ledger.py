"""Simple test to debug ledger entity issues."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from uuid import uuid4
from domain.poker.value_objects import GameId
from domain.ledger.entities import LedgerEntry, SessionLedger

def test_simple_creation():
    """Test simple creation of ledger entry."""
    game_id = GameId(str(uuid4()))

    entry = LedgerEntry.create_new(
        session_id=str(uuid4()),
        player_id=str(uuid4()),
        game_id=game_id,
        external_id="test-session",
        game_number=1,
        display_name="Test Player",
        session_names=["Test"],
        buy_in_sum=5000,
        cash_out_sum=6000,
        in_game=0
    )

    print("✅ LedgerEntry created successfully")
    print(f"Session ID: {entry.get_session_id()}")
    print(f"Player ID: {entry.get_player_id()}")
    print(f"Is Profitable: {entry.is_profitable()}")

if __name__ == "__main__":
    test_simple_creation()