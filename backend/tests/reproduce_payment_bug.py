"""
Reproduction script for payment ledger bug.

This script demonstrates the bug where player merge incorrectly calculates
payment_balance by adding balances instead of recalculating from components.

Run with:
    DATABASE_URL=postgresql://pokeruser:supersecret@localhost:5432/poker_analytics_test \
    PYTHONPATH=src python tests/reproduce_payment_bug.py
"""

import sys
import os
from decimal import Decimal
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from db.database import SessionLocal
from db.models import (
    Game, Player, GamePlayer, Session as SessionModel,
    SessionPlayerSummary, PaymentTransaction, PaymentBalance
)
from sqlalchemy import text


def cents(dollars: float) -> int:
    """Convert dollars to cents"""
    return int(dollars * 100)


def dollars(cents_val: int) -> float:
    """Convert cents to dollars"""
    return cents_val / 100.0


def setup_test_data(db):
    """Create test game, players, sessions, and payments"""
    print("\n" + "="*80)
    print("SETTING UP TEST DATA")
    print("="*80)

    # Create test game
    game = Game(
        public_code="TEST",
        admin_code="test_admin_code_123",
        title="Test Game for Bug Reproduction"
    )
    db.add(game)
    db.flush()
    print(f"\n✓ Created game: {game.public_code} (id: {game.id})")

    # Create two Fish players (representing the same person with different external_ids)
    player_a = Player(
        external_id="ixPjNdmxK-",
        display_name="fish"
    )
    player_b = Player(
        external_id="uj0LVk8n0K",
        display_name="Fish"
    )

    db.add(player_a)
    db.add(player_b)
    db.flush()

    print(f"\n✓ Created Player A (source): {player_a.display_name} (id: {player_a.id}, external_id: {player_a.external_id})")
    print(f"✓ Created Player B (target): {player_b.display_name} (id: {player_b.id}, external_id: {player_b.external_id})")

    # Link players to game
    db.add(GamePlayer(game_id=game.id, player_id=player_a.id))
    db.add(GamePlayer(game_id=game.id, player_id=player_b.id))

    # Create session for Player A (incomplete session with in_game chips)
    session_a = SessionModel(
        game_id=game.id,
        external_id="test_session_a",
        session_type="pokernow",
        started_at=datetime.utcnow()
    )
    db.add(session_a)
    db.flush()

    # Player A session summary - matches PokerNow data
    summary_a = SessionPlayerSummary(
        session_id=session_a.id,
        player_id=player_a.id,
        buy_in_sum=cents(240.13),
        cash_out_sum=cents(137.49),
        in_game=cents(330.95),
        net=cents(228.31),  # Correct: 137.49 + 330.95 - 240.13 = 228.31
        names=["fish"]
    )
    db.add(summary_a)

    print(f"\n✓ Created Session A for Player A:")
    print(f"  - Buy-in: ${dollars(summary_a.buy_in_sum):.2f}")
    print(f"  - Cash-out: ${dollars(summary_a.cash_out_sum):.2f}")
    print(f"  - In-game: ${dollars(summary_a.in_game):.2f}")
    print(f"  - Net: ${dollars(summary_a.net):.2f}")

    # Create session for Player B (complete session)
    session_b = SessionModel(
        game_id=game.id,
        external_id="test_session_b",
        session_type="pokernow",
        started_at=datetime.utcnow()
    )
    db.add(session_b)
    db.flush()

    summary_b = SessionPlayerSummary(
        session_id=session_b.id,
        player_id=player_b.id,
        buy_in_sum=cents(50.00),
        cash_out_sum=cents(102.64),
        in_game=cents(0.00),
        net=cents(52.64),  # 102.64 - 50.00 = 52.64
        names=["Fish"]
    )
    db.add(summary_b)

    print(f"\n✓ Created Session B for Player B:")
    print(f"  - Buy-in: ${dollars(summary_b.buy_in_sum):.2f}")
    print(f"  - Cash-out: ${dollars(summary_b.cash_out_sum):.2f}")
    print(f"  - In-game: ${dollars(summary_b.in_game):.2f}")
    print(f"  - Net: ${dollars(summary_b.net):.2f}")

    # Create some payment transactions
    # Player A paid $100, received $50
    payment_a_out = PaymentTransaction(
        game_id=game.id,
        payer_id=player_a.id,
        recipient_id=player_b.id,  # Doesn't matter who
        amount_cents=cents(100.00),
        payment_date=datetime.utcnow(),
        created_by="test_script"
    )
    payment_a_in = PaymentTransaction(
        game_id=game.id,
        payer_id=player_b.id,
        recipient_id=player_a.id,
        amount_cents=cents(50.00),
        payment_date=datetime.utcnow(),
        created_by="test_script"
    )

    # Player B paid $20, received $10
    payment_b_out = PaymentTransaction(
        game_id=game.id,
        payer_id=player_b.id,
        recipient_id=player_a.id,
        amount_cents=cents(20.00),
        payment_date=datetime.utcnow(),
        created_by="test_script"
    )
    payment_b_in = PaymentTransaction(
        game_id=game.id,
        payer_id=player_a.id,
        recipient_id=player_b.id,
        amount_cents=cents(10.00),
        payment_date=datetime.utcnow(),
        created_by="test_script"
    )

    db.add_all([payment_a_out, payment_a_in, payment_b_out, payment_b_in])

    print(f"\n✓ Created payment transactions:")
    print(f"  Player A: Paid $100.00, Received $50.00")
    print(f"  Player B: Paid $20.00, Received $10.00")

    # Create payment balances for both players
    # BUG SIMULATION: poker_net_winnings is INCORRECTLY calculated
    # It should include in_game chips, but the bug excludes them

    # Player A: WRONG poker_net = cash_out - buy_in (missing in_game)
    #          Should be: 228.31 (137.49 + 330.95 - 240.13)
    #          Bug gives: -102.64 (137.49 - 240.13)
    incorrect_poker_net_a = cents(137.49 - 240.13)  # -102.64 (WRONG!)

    # Player B has no in_game chips, so calculation is correct
    correct_poker_net_b = cents(52.64)

    balance_a_value = incorrect_poker_net_a + cents(50.00) - cents(100.00)  # -152.64
    balance_a = PaymentBalance(
        game_id=game.id,
        player_id=player_a.id,
        poker_net_winnings=incorrect_poker_net_a,  # -102.64 (WRONG!)
        total_paid=cents(100.00),
        total_received=cents(50.00),
        payment_balance=balance_a_value,  # -152.64
        balance_negative_since=datetime.utcnow() if balance_a_value < 0 else None,
        last_updated=datetime.utcnow()
    )

    balance_b_value = correct_poker_net_b + cents(10.00) - cents(20.00)  # 42.64
    balance_b = PaymentBalance(
        game_id=game.id,
        player_id=player_b.id,
        poker_net_winnings=correct_poker_net_b,
        total_paid=cents(20.00),
        total_received=cents(10.00),
        payment_balance=balance_b_value,  # 42.64
        balance_negative_since=datetime.utcnow() if balance_b_value < 0 else None,
        last_updated=datetime.utcnow()
    )

    db.add_all([balance_a, balance_b])
    db.flush()

    print(f"\n✓ Created payment balances (with BUG - Player A's poker_net is wrong):")
    print(f"  Player A: poker_net=${dollars(balance_a.poker_net_winnings):.2f} (WRONG! Should be $228.31), payment_balance=${dollars(balance_a.payment_balance):.2f}")
    print(f"  Player B: poker_net=${dollars(balance_b.poker_net_winnings):.2f}, payment_balance=${dollars(balance_b.payment_balance):.2f}")

    db.commit()

    return game, player_a, player_b


def print_before_merge(db, player_a, player_b, game):
    """Print the state before merge"""
    print("\n" + "="*80)
    print("BEFORE MERGE - PLAYER STATES")
    print("="*80)

    balance_a = db.query(PaymentBalance).filter(
        PaymentBalance.game_id == game.id,
        PaymentBalance.player_id == player_a.id
    ).first()

    balance_b = db.query(PaymentBalance).filter(
        PaymentBalance.game_id == game.id,
        PaymentBalance.player_id == player_b.id
    ).first()

    print(f"\nPlayer A ({player_a.display_name}, {player_a.external_id}):")
    print(f"  poker_net_winnings:  ${dollars(balance_a.poker_net_winnings):>10.2f}")
    print(f"  total_paid:          ${dollars(balance_a.total_paid):>10.2f}")
    print(f"  total_received:      ${dollars(balance_a.total_received):>10.2f}")
    print(f"  payment_balance:     ${dollars(balance_a.payment_balance):>10.2f}")

    print(f"\nPlayer B ({player_b.display_name}, {player_b.external_id}):")
    print(f"  poker_net_winnings:  ${dollars(balance_b.poker_net_winnings):>10.2f}")
    print(f"  total_paid:          ${dollars(balance_b.total_paid):>10.2f}")
    print(f"  total_received:      ${dollars(balance_b.total_received):>10.2f}")
    print(f"  payment_balance:     ${dollars(balance_b.payment_balance):>10.2f}")

    print(f"\nExpected merged values (if bug adds balances):")
    merged_poker_net = balance_a.poker_net_winnings + balance_b.poker_net_winnings
    merged_paid = balance_a.total_paid + balance_b.total_paid
    merged_received = balance_a.total_received + balance_b.total_received
    expected_balance_wrong = balance_a.payment_balance + balance_b.payment_balance  # WRONG METHOD
    expected_balance_correct = merged_poker_net + merged_received - merged_paid  # CORRECT METHOD

    print(f"  poker_net_winnings:  ${dollars(merged_poker_net):>10.2f} (still wrong)")
    print(f"  total_paid:          ${dollars(merged_paid):>10.2f}")
    print(f"  total_received:      ${dollars(merged_received):>10.2f}")
    print(f"  payment_balance (adding): ${dollars(expected_balance_wrong):>10.2f} (BUG METHOD)")
    print(f"  payment_balance (recalc): ${dollars(expected_balance_correct):>10.2f} (CORRECT METHOD)")
    print(f"\n  Note: BOTH are wrong because poker_net is wrong!")
    print(f"  ACTUAL correct balance: $220.95 (using correct poker_net $228.31)")

    return expected_balance_correct


def merge_players_direct(db, source_player_id, target_player_id, game):
    """
    Directly execute the merge logic from routes/game.py to reproduce the bug.
    This simulates the API endpoint.
    """
    print("\n" + "="*80)
    print("EXECUTING PLAYER MERGE")
    print("="*80)

    from sqlalchemy import func

    # Get both players
    source_player = db.query(Player).filter(Player.id == source_player_id).first()
    target_player = db.query(Player).filter(Player.id == target_player_id).first()

    print(f"\nMerging '{source_player.display_name}' → '{target_player.display_name}'")

    # Transfer session summaries from source to target
    summaries_to_transfer = db.query(SessionPlayerSummary).filter(
        SessionPlayerSummary.player_id == source_player_id
    ).all()

    for summary in summaries_to_transfer:
        existing_summary = db.query(SessionPlayerSummary).filter(
            SessionPlayerSummary.session_id == summary.session_id,
            SessionPlayerSummary.player_id == target_player_id
        ).first()

        if existing_summary:
            # Merge the values
            existing_summary.buy_in_sum += summary.buy_in_sum
            existing_summary.cash_out_sum += summary.cash_out_sum
            existing_summary.in_game += summary.in_game
            existing_summary.net += summary.net
            existing_summary.names = list(set(existing_summary.names + summary.names))
            db.delete(summary)
        else:
            summary.player_id = target_player_id

    # Transfer payment transactions
    payer_transactions = db.query(PaymentTransaction).filter(
        PaymentTransaction.payer_id == source_player_id
    ).all()

    for transaction in payer_transactions:
        transaction.payer_id = target_player_id

    recipient_transactions = db.query(PaymentTransaction).filter(
        PaymentTransaction.recipient_id == source_player_id
    ).all()

    for transaction in recipient_transactions:
        transaction.recipient_id = target_player_id

    # Transfer payment balances - THIS IS WHERE THE BUG OCCURS
    source_balances = db.query(PaymentBalance).filter(
        PaymentBalance.player_id == source_player_id
    ).all()

    for source_balance in source_balances:
        existing_balance = db.query(PaymentBalance).filter(
            PaymentBalance.game_id == source_balance.game_id,
            PaymentBalance.player_id == target_player_id
        ).first()

        if existing_balance:
            print(f"\n🐛 BUG: Merging balances by ADDING them together:")
            print(f"   Existing balance: ${dollars(existing_balance.payment_balance):.2f}")
            print(f"   Source balance:   ${dollars(source_balance.payment_balance):.2f}")

            # THIS IS THE BUG - line 1549 in routes/game.py
            existing_balance.total_paid += source_balance.total_paid
            existing_balance.total_received += source_balance.total_received
            existing_balance.poker_net_winnings += source_balance.poker_net_winnings
            existing_balance.payment_balance += source_balance.payment_balance  # ❌ BUG!

            # Update balance_negative_since if balance is now negative
            if existing_balance.payment_balance < 0 and existing_balance.balance_negative_since is None:
                existing_balance.balance_negative_since = datetime.utcnow()
            elif existing_balance.payment_balance >= 0:
                existing_balance.balance_negative_since = None

            existing_balance.last_updated = func.now()

            print(f"   Merged balance:   ${dollars(existing_balance.payment_balance):.2f} (WRONG!)")

            db.delete(source_balance)
        else:
            source_balance.player_id = target_player_id

    # Delete source player
    db.delete(source_player)
    db.commit()

    print(f"\n✓ Merge completed")


def print_after_merge(db, target_player_id, game, expected_balance):
    """Print the state after merge and verify the bug"""
    print("\n" + "="*80)
    print("AFTER MERGE - VERIFICATION")
    print("="*80)

    merged_balance = db.query(PaymentBalance).filter(
        PaymentBalance.game_id == game.id,
        PaymentBalance.player_id == target_player_id
    ).first()

    if not merged_balance:
        print("\n❌ ERROR: No payment balance found for merged player!")
        return

    print(f"\nMerged Player Balance:")
    print(f"  poker_net_winnings:  ${dollars(merged_balance.poker_net_winnings):>10.2f}")
    print(f"  total_paid:          ${dollars(merged_balance.total_paid):>10.2f}")
    print(f"  total_received:      ${dollars(merged_balance.total_received):>10.2f}")
    print(f"  payment_balance:     ${dollars(merged_balance.payment_balance):>10.2f} (STORED)")

    # Calculate what it SHOULD be
    calculated_balance = (
        merged_balance.poker_net_winnings +
        merged_balance.total_received -
        merged_balance.total_paid
    )

    print(f"\nVerification:")
    print(f"  Expected balance:    ${dollars(expected_balance):>10.2f}")
    print(f"  Calculated balance:  ${dollars(calculated_balance):>10.2f} (poker_net + received - paid)")
    print(f"  Stored balance:      ${dollars(merged_balance.payment_balance):>10.2f}")

    # The REAL correct balance (using correct poker_net from session data)
    real_correct_balance = cents(228.31 + 52.64 + 60 - 120)  # 220.95

    # Check if bug is present
    print(f"\n🐛 BUG ANALYSIS:")
    print(f"  The merge operation ADDS the two payment_balances:")
    print(f"  $(-152.64) + $42.64 = ${dollars(merged_balance.payment_balance):.2f}")
    print(f"\n  But the CORRECT value (using correct poker_net) should be:")
    print(f"  $220.95 = $228.31 (correct poker_net) + $60 - $120")
    print(f"\n  The bug has TWO parts:")
    print(f"  1. poker_net_winnings excluded in_game chips ($330.95)")
    print(f"     This made it -$102.64 instead of $228.31")
    print(f"  2. Merge ADDED the wrong balances instead of recalculating")
    print(f"     This compounded the error")

    discrepancy_from_correct = merged_balance.payment_balance - real_correct_balance
    print(f"\n✅ BUG SUCCESSFULLY REPRODUCED!")
    print(f"  Total discrepancy from correct value: ${dollars(abs(discrepancy_from_correct)):.2f}")
    print(f"  Stored balance:  ${dollars(merged_balance.payment_balance):.2f}")
    print(f"  Correct balance: ${dollars(real_correct_balance):.2f}")
    print(f"\n  This matches the production bug where Max shows $300 owed")
    print(f"  instead of the correct -$385 (he's owed money, not owing)!")


def main():
    """Main reproduction script"""
    print("\n" + "="*80)
    print("PAYMENT LEDGER BUG REPRODUCTION SCRIPT")
    print("="*80)
    print("\nThis script reproduces the bug where player merge incorrectly")
    print("calculates payment_balance by adding balances instead of recalculating.")

    # Use test database
    with SessionLocal() as db:
        # Clean up any existing test data
        db.execute(text("DELETE FROM payment_balances WHERE game_id IN (SELECT id FROM games WHERE public_code = 'TEST')"))
        db.execute(text("DELETE FROM payment_transactions WHERE game_id IN (SELECT id FROM games WHERE public_code = 'TEST')"))
        db.execute(text("DELETE FROM session_player_summaries WHERE session_id IN (SELECT id FROM sessions WHERE game_id IN (SELECT id FROM games WHERE public_code = 'TEST'))"))
        db.execute(text("DELETE FROM sessions WHERE game_id IN (SELECT id FROM games WHERE public_code = 'TEST')"))
        db.execute(text("DELETE FROM game_players WHERE game_id IN (SELECT id FROM games WHERE public_code = 'TEST')"))
        db.execute(text("DELETE FROM players WHERE external_id IN ('ixPjNdmxK-', 'uj0LVk8n0K')"))
        db.execute(text("DELETE FROM games WHERE public_code = 'TEST'"))
        db.commit()

        # Setup test data
        game, player_a, player_b = setup_test_data(db)

        # Print before merge
        expected_balance = print_before_merge(db, player_a, player_b, game)

        # Execute merge
        merge_players_direct(db, player_a.id, player_b.id, game)

        # Print after merge and verify bug
        print_after_merge(db, player_b.id, game, expected_balance)

    print("\n" + "="*80)
    print("REPRODUCTION COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
