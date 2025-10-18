#!/usr/bin/env python3
"""
Test script for merge_duplicate_players.py

Creates test data with duplicate players and verifies the merge script works.
"""

import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from db.database import SessionLocal
from db.models import Game, Player, Session, SessionPlayerSummary

def create_test_data():
    """Create test game with duplicate players."""
    db = SessionLocal()

    try:
        # Create test game
        unique_id = str(uuid.uuid4())[:8].upper()
        game = Game(
            public_code=f"MERGE{unique_id}",
            admin_code=f"ADM{unique_id}",
            title=f"Merge Test Game {unique_id}"
        )
        db.add(game)
        db.flush()

        print(f"Created game: {game.public_code}")

        # Create duplicate "Remy" players (case-sensitivity issue)
        remy1 = Player(
            display_name="Remy",
            external_id="lw0lJXpCtc"  # lowercase 'c'
        )
        remy2 = Player(
            display_name="REMY",
            external_id="lw0lJXpCtC"  # uppercase 'C'
        )
        db.add(remy1)
        db.add(remy2)
        db.flush()

        # Create duplicate "Trevor" players (different external_ids)
        trevor1 = Player(
            display_name="Trevor",
            external_id="UxssJN_W8d"
        )
        trevor2 = Player(
            display_name="Trevor",
            external_id="_yJfKHdotT"
        )
        db.add(trevor1)
        db.add(trevor2)
        db.flush()

        # Create another player (no duplicate)
        alice = Player(
            display_name="Alice",
            external_id="alice123"
        )
        db.add(alice)
        db.flush()

        # Create sessions for old Remy (should be keeper - more sessions)
        for i in range(5):
            session = Session(
                game_id=game.id,
                external_id=f"session_remy1_{i}",
                session_type="cash_game"
            )
            db.add(session)
            db.flush()

            summary = SessionPlayerSummary(
                session_id=session.id,
                player_id=remy1.id,
                buy_in_sum=10000,
                cash_out_sum=12000,
                in_game=0,
                net=2000,
                names=["Remy"]
            )
            db.add(summary)

        # Create 1 session for new Remy (should be merged)
        session = Session(
            game_id=game.id,
            external_id="session_remy2_1",
            session_type="cash_game"
        )
        db.add(session)
        db.flush()

        summary = SessionPlayerSummary(
            session_id=session.id,
            player_id=remy2.id,
            buy_in_sum=10000,
            cash_out_sum=8000,
            in_game=0,
            net=-2000,
            names=["REMY"]
        )
        db.add(summary)

        # Create sessions for old Trevor (should be keeper - more sessions)
        for i in range(3):
            session = Session(
                game_id=game.id,
                external_id=f"session_trevor1_{i}",
                session_type="cash_game"
            )
            db.add(session)
            db.flush()

            summary = SessionPlayerSummary(
                session_id=session.id,
                player_id=trevor1.id,
                buy_in_sum=10000,
                cash_out_sum=11000,
                in_game=0,
                net=1000,
                names=["Trevor"]
            )
            db.add(summary)

        # Create 1 session for new Trevor (should be merged)
        session = Session(
            game_id=game.id,
            external_id="session_trevor2_1",
            session_type="cash_game"
        )
        db.add(session)
        db.flush()

        summary = SessionPlayerSummary(
            session_id=session.id,
            player_id=trevor2.id,
            buy_in_sum=10000,
            cash_out_sum=9000,
            in_game=0,
            net=-1000,
            names=["Trevor"]
        )
        db.add(summary)

        # Create session for Alice (no duplicates)
        session = Session(
            game_id=game.id,
            external_id="session_alice_1",
            session_type="cash_game"
        )
        db.add(session)
        db.flush()

        summary = SessionPlayerSummary(
            session_id=session.id,
            player_id=alice.id,
            buy_in_sum=10000,
            cash_out_sum=10500,
            in_game=0,
            net=500,
            names=["Alice"]
        )
        db.add(summary)

        db.commit()

        print(f"\nTest data created successfully!")
        print(f"\nDuplicate sets:")
        print(f"  Remy: {remy1.id} (5 sessions) + {remy2.id} (1 session)")
        print(f"  Trevor: {trevor1.id} (3 sessions) + {trevor2.id} (1 session)")
        print(f"  Alice: {alice.id} (1 session) - no duplicates")
        print(f"\nRun the merge script:")
        print(f"  PYTHONPATH=src python merge_duplicate_players.py --game-code {game.public_code} --dry-run")

        return game.public_code

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()


if __name__ == "__main__":
    if not os.getenv("DATABASE_URL"):
        print("ERROR: DATABASE_URL environment variable must be set")
        print("Example: export DATABASE_URL=postgresql+psycopg2://user@127.0.0.1:5432/poker_analytics_test")
        sys.exit(1)

    create_test_data()
