#!/usr/bin/env python
"""
Demo script to test the balance_negative_since timestamp fix.

This script:
1. Creates test data with a negative balance player
2. Verifies the timestamp is set correctly
3. Makes multiple payments while balance stays negative
4. Confirms timestamp is PRESERVED (not reset to NOW)

Run with: DATABASE_URL=postgresql+psycopg2://pokeruser:supersecret@localhost:5432/poker_analytics python test_timestamp_fix_demo.py
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from db.database import SessionLocal
from db.models import Game, Player, Session, SessionPlayerSummary, PaymentBalance
from services.payment_service_v2 import PaymentService

def main():
    print("=" * 80)
    print("Testing balance_negative_since Timestamp Preservation Fix")
    print("=" * 80)

    db = SessionLocal()

    try:
        # Clean up: Delete test data if it exists
        print("\n[1] Cleaning up any existing test data...")
        unique_id = str(uuid.uuid4())[:8].upper()

        # Create test game
        print(f"\n[2] Creating test game with ID: {unique_id}")
        game = Game(
            public_code=f"TEST{unique_id}",
            admin_code=f"ADM{unique_id}",
            title=f"Timestamp Fix Test {unique_id}"
        )
        db.add(game)
        db.flush()
        print(f"   ✓ Game created with ID: {game.id}")

        # Create two players
        print("\n[3] Creating test players...")
        alice = Player(
            display_name=f"Alice_{unique_id}",
            external_id=f"alice_ts_fix_{unique_id}"
        )
        bob = Player(
            display_name=f"Bob_{unique_id}",
            external_id=f"bob_ts_fix_{unique_id}"
        )
        db.add(alice)
        db.add(bob)
        db.flush()
        print(f"   ✓ Alice created with ID: {alice.id}")
        print(f"   ✓ Bob created with ID: {bob.id}")

        # Create session with poker results: Alice +$100, Bob -$100
        print("\n[4] Creating poker session...")
        session = Session(
            game_id=game.id,
            external_id=f"ts_fix_session_{unique_id}",
            session_type="cash_game"
        )
        db.add(session)
        db.flush()

        # Alice wins $100
        alice_summary = SessionPlayerSummary(
            session_id=session.id,
            player_id=alice.id,
            buy_in_sum=100000,  # $1000
            cash_out_sum=110000,  # $1100
            in_game=0,
            net=10000,  # +$100
            names=[alice.display_name]
        )
        db.add(alice_summary)

        # Bob loses $100
        bob_summary = SessionPlayerSummary(
            session_id=session.id,
            player_id=bob.id,
            buy_in_sum=100000,  # $1000
            cash_out_sum=90000,  # $900
            in_game=0,
            net=-10000,  # -$100
            names=[bob.display_name]
        )
        db.add(bob_summary)
        db.commit()
        print(f"   ✓ Session created: Alice +$100, Bob -$100")

        # Initialize payment service (V2)
        print("\n[5] Initializing payment service (V2 with fix)...")
        service = PaymentService(db)

        # Update balances to persist them (including timestamps)
        print("\n[6] Triggering balance update to persist timestamps...")
        from infrastructure.persistence.sqlalchemy.payment_repository import SQLAlchemyPaymentBalanceRepository
        from domain.poker.value_objects import GameId, PlayerId
        balance_repo = SQLAlchemyPaymentBalanceRepository(db)
        balance_repo.update_balances_for_players(
            GameId(str(game.id)),
            [PlayerId(str(alice.id)), PlayerId(str(bob.id))]
        )
        db.commit()

        # Get initial balances - timestamps should now be persisted
        print("\n[7] Reading persisted balances...")
        summary = service.get_payment_summary(str(game.id))
        bob_summary_data = next(p for p in summary if p.player_id == str(bob.id))
        print(f"   ✓ Bob's balance: ${bob_summary_data.balance}")
        assert bob_summary_data.balance == Decimal('-100.00'), "Bob should have -$100 balance"

        # Get Bob's balance record with timestamp
        balance_record = db.query(PaymentBalance).filter(
            PaymentBalance.player_id == bob.id,
            PaymentBalance.game_id == game.id
        ).first()

        if not balance_record or balance_record.balance_negative_since is None:
            print("   ✗ ERROR: balance_negative_since is NULL!")
            print("   This means the timestamp wasn't set when balance became negative.")
            return False

        original_timestamp = balance_record.balance_negative_since
        print(f"   ✓ balance_negative_since set to: {original_timestamp}")
        print(f"   ✓ Balance has been negative for: {(datetime.now(timezone.utc) - original_timestamp).total_seconds():.1f} seconds")

        # Wait a moment to ensure timestamps would differ if reset
        print("\n[8] Waiting 2 seconds...")
        time.sleep(2)

        # Make a payment that keeps Bob negative (but less negative)
        print("\n[9] Recording payment: Bob pays Alice $30...")
        print("    Bob's balance will go from -$100 to -$70 (still negative)")
        service.record_payment(
            game_id=str(game.id),
            payer_id=str(bob.id),
            recipient_id=str(alice.id),
            amount=Decimal('30.00'),
            payment_date=datetime.now(timezone.utc)
        )
        print("   ✓ Payment recorded")

        # Check that timestamp was PRESERVED
        db.refresh(balance_record)
        new_timestamp = balance_record.balance_negative_since
        new_balance = balance_record.payment_balance

        print("\n[10] Verifying timestamp preservation...")
        print(f"   Original timestamp: {original_timestamp}")
        print(f"   Current timestamp:  {new_timestamp}")
        print(f"   New balance: ${new_balance / 100:.2f}")

        if new_timestamp != original_timestamp:
            print("   ✗ FAIL: Timestamp was reset!")
            print(f"   Time difference: {(new_timestamp - original_timestamp).total_seconds()} seconds")
            print("   This is the BUG we're trying to fix.")
            return False

        print("   ✓ PASS: Timestamp preserved correctly!")
        print(f"   ✓ Balance changed from -$100 to -${abs(new_balance / 100):.2f}")
        print(f"   ✓ Timestamp still shows Bob has been negative for: {(datetime.now(timezone.utc) - new_timestamp).total_seconds():.1f} seconds")

        # Make another payment
        print("\n[11] Recording another payment: Bob pays Alice $20...")
        time.sleep(1)
        service.record_payment(
            game_id=str(game.id),
            payer_id=str(bob.id),
            recipient_id=str(alice.id),
            amount=Decimal('20.00'),
            payment_date=datetime.now(timezone.utc)
        )

        db.refresh(balance_record)
        final_timestamp = balance_record.balance_negative_since
        final_balance = balance_record.payment_balance

        print(f"   ✓ Payment recorded")
        print(f"   Final balance: ${final_balance / 100:.2f}")

        if final_timestamp != original_timestamp:
            print("   ✗ FAIL: Timestamp was reset on second payment!")
            return False

        print("   ✓ PASS: Timestamp still preserved after multiple payments!")

        # Final verification
        print("\n" + "=" * 80)
        print("FINAL VERIFICATION")
        print("=" * 80)
        print(f"Original timestamp:  {original_timestamp}")
        print(f"Current timestamp:   {final_timestamp}")
        print(f"Timestamps match:    {original_timestamp == final_timestamp}")
        print(f"Original balance:    -$100.00")
        print(f"Final balance:       ${final_balance / 100:.2f}")
        print(f"Total days negative: {(datetime.now(timezone.utc) - final_timestamp).days} days")

        if original_timestamp == final_timestamp:
            print("\n✅ SUCCESS: The timestamp fix is working correctly!")
            print("The balance_negative_since timestamp was preserved through multiple")
            print("balance updates while the balance stayed negative.")
            return True
        else:
            print("\n❌ FAILURE: The bug still exists!")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    # Check DATABASE_URL is set
    if not os.getenv("DATABASE_URL"):
        print("ERROR: DATABASE_URL environment variable must be set")
        print("Example: DATABASE_URL=postgresql+psycopg2://pokeruser:supersecret@localhost:5432/poker_analytics")
        sys.exit(1)

    # Set USE_DOMAIN_SERVICES to use V2 service with the fix
    os.environ["USE_DOMAIN_SERVICES"] = "true"

    success = main()
    sys.exit(0 if success else 1)
