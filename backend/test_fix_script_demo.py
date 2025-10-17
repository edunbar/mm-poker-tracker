#!/usr/bin/env python
"""
Test script to verify fix_balance_timestamps.py works correctly.

This script:
1. Creates test data with corrupted timestamps (mimicking production bug)
2. Runs the fix script
3. Verifies the timestamps were corrected

Run with: DATABASE_URL=postgresql+psycopg2://pokeruser:supersecret@localhost:5432/poker_analytics_test python test_fix_script_demo.py
"""

import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from db.database import SessionLocal
from db.models import Game, Player, Session, SessionPlayerSummary, PaymentBalance, PaymentTransaction
from fix_balance_timestamps import fix_balance_timestamps

def main():
    print("=" * 80)
    print("Testing fix_balance_timestamps.py Script")
    print("=" * 80)

    db = SessionLocal()

    try:
        # Create test game
        unique_id = str(uuid.uuid4())[:8].upper()
        print(f"\n[1] Creating test game with ID: {unique_id}")
        game = Game(
            public_code=f"FIX{unique_id}",
            admin_code=f"ADM{unique_id}",
            title=f"Fix Script Test {unique_id}"
        )
        db.add(game)
        db.flush()
        print(f"   ✓ Game created: {game.public_code}")

        # Create two players
        print("\n[2] Creating test players...")
        alice = Player(
            display_name=f"Alice_{unique_id}",
            external_id=f"alice_fix_{unique_id}"
        )
        bob = Player(
            display_name=f"Bob_{unique_id}",
            external_id=f"bob_fix_{unique_id}"
        )
        db.add(alice)
        db.add(bob)
        db.flush()
        print(f"   ✓ Alice and Bob created")

        # Create session with poker results: Alice +$200, Bob -$200
        print("\n[3] Creating poker session...")
        session = Session(
            game_id=game.id,
            external_id=f"fix_session_{unique_id}",
            session_type="cash_game"
        )
        db.add(session)
        db.flush()

        alice_summary = SessionPlayerSummary(
            session_id=session.id,
            player_id=alice.id,
            buy_in_sum=100000,
            cash_out_sum=120000,  # +$200
            in_game=0,
            net=20000,
            names=[alice.display_name]
        )
        bob_summary = SessionPlayerSummary(
            session_id=session.id,
            player_id=bob.id,
            buy_in_sum=100000,
            cash_out_sum=80000,  # -$200
            in_game=0,
            net=-20000,
            names=[bob.display_name]
        )
        db.add(alice_summary)
        db.add(bob_summary)
        db.flush()
        print(f"   ✓ Session created: Alice +$200, Bob -$200")

        # Create payment transactions over time (Bob gradually pays Alice)
        print("\n[4] Creating payment transaction history...")

        # Transaction 1: Bob pays Alice $50 (10 days ago)
        ten_days_ago = datetime.now(timezone.utc) - timedelta(days=10)
        txn1 = PaymentTransaction(
            game_id=game.id,
            payer_id=bob.id,
            recipient_id=alice.id,
            amount_cents=5000,  # $50
            payment_date=ten_days_ago,
            status='completed',
            created_at=ten_days_ago,
            created_by='test_script'
        )
        db.add(txn1)
        print(f"   ✓ Transaction 1: Bob pays $50 (10 days ago)")

        # Transaction 2: Bob pays Alice $30 (5 days ago)
        five_days_ago = datetime.now(timezone.utc) - timedelta(days=5)
        txn2 = PaymentTransaction(
            game_id=game.id,
            payer_id=bob.id,
            recipient_id=alice.id,
            amount_cents=3000,  # $30
            payment_date=five_days_ago,
            status='completed',
            created_at=five_days_ago,
            created_by='test_script'
        )
        db.add(txn2)
        print(f"   ✓ Transaction 2: Bob pays $30 (5 days ago)")

        db.flush()

        # Create corrupted PaymentBalance records (negative balance but NULL timestamp)
        print("\n[5] Creating corrupted PaymentBalance records...")

        # Alice: +$200 poker, +$80 payments received = +$120 balance (positive, no timestamp)
        alice_balance = PaymentBalance(
            game_id=game.id,
            player_id=alice.id,
            poker_net_winnings=20000,  # $200
            total_paid=0,
            total_received=8000,  # $80
            payment_balance=12000,  # +$120
            balance_negative_since=None  # Correctly NULL
        )
        db.add(alice_balance)

        # Bob: -$200 poker, +$80 paid = -$120 balance (negative, but NULL timestamp - BUG!)
        bob_balance = PaymentBalance(
            game_id=game.id,
            player_id=bob.id,
            poker_net_winnings=-20000,  # -$200
            total_paid=8000,  # $80
            total_received=0,
            payment_balance=-12000,  # -$120
            balance_negative_since=None  # ❌ BUG: Should be set!
        )
        db.add(bob_balance)
        db.commit()
        print(f"   ✓ Bob has -$120 balance with NULL timestamp (mimics production bug)")

        # Verify corrupted state
        print("\n[6] Verifying corrupted state...")
        corrupted = db.query(PaymentBalance).filter(
            PaymentBalance.game_id == game.id,
            PaymentBalance.payment_balance < 0,
            PaymentBalance.balance_negative_since.is_(None)
        ).count()
        print(f"   ✓ Found {corrupted} players with negative balance and NULL timestamp")

        # Run fix script (dry run first)
        print("\n[7] Running fix script (dry run)...")
        fix_balance_timestamps(game_code=game.public_code, dry_run=True)

        # Run fix script (actual update)
        print("\n[8] Running fix script (live update)...")
        fix_balance_timestamps(game_code=game.public_code, dry_run=False)

        # Verify fix
        print("\n[9] Verifying fix...")
        db.refresh(bob_balance)

        if bob_balance.balance_negative_since is None:
            print("   ✗ FAIL: Timestamp still NULL!")
            return False

        print(f"   ✓ Bob's timestamp set to: {bob_balance.balance_negative_since}")

        # The timestamp should be 10 days ago (when first transaction occurred and balance was still negative)
        # Bob started at -$200, paid $50 10 days ago (now -$150), paid $30 5 days ago (now -$120)
        # So balance has been negative since the session (before any payments)
        # Since we don't have a timestamp for the session, the script should use the first transaction
        expected_days = 10
        actual_days = (datetime.now(timezone.utc) - bob_balance.balance_negative_since).days

        print(f"   ✓ Days negative: {actual_days} (expected ~{expected_days})")

        if actual_days >= expected_days - 1 and actual_days <= expected_days + 1:
            print("\n" + "=" * 80)
            print("✅ SUCCESS: The fix script is working correctly!")
            print("The script correctly calculated the historical timestamp from transaction history.")
            print("=" * 80)
            return True
        else:
            print(f"\n   ✗ FAIL: Expected ~{expected_days} days but got {actual_days}")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    if not os.getenv("DATABASE_URL"):
        print("ERROR: DATABASE_URL environment variable must be set")
        sys.exit(1)

    success = main()
    sys.exit(0 if success else 1)
