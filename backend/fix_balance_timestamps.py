#!/usr/bin/env python3
"""
Fix balance_negative_since Timestamps

This script recalculates balance_negative_since timestamps by replaying
payment transaction history chronologically to find the exact date when
each player's balance first became negative.

Usage:
    # Dry run (shows what would change, no updates):
    PYTHONPATH=src python fix_balance_timestamps.py --dry-run

    # Actually update the database:
    PYTHONPATH=src python fix_balance_timestamps.py

    # For a specific game:
    PYTHONPATH=src python fix_balance_timestamps.py --game-code C4QRO
"""

import argparse
import sys
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Tuple
from dataclasses import dataclass

from sqlalchemy import func
from db.database import SessionLocal
from db.models import (
    Game, Player, PaymentTransaction, PaymentBalance,
    SessionPlayerSummary, Session
)


@dataclass
class TransactionEvent:
    """Represents a payment transaction event"""
    timestamp: datetime
    amount_cents: int  # Positive if player pays, negative if player receives
    transaction_id: str
    description: str


def calculate_poker_winnings(db, game_id: str, player_id: str) -> int:
    """Calculate total poker winnings from all sessions (in cents)"""
    result = (
        db.query(func.coalesce(func.sum(SessionPlayerSummary.net), 0))
        .join(Session, SessionPlayerSummary.session_id == Session.id)
        .filter(
            Session.game_id == game_id,
            SessionPlayerSummary.player_id == player_id
        )
        .scalar()
    )
    return result or 0


def get_payment_events(db, game_id: str, player_id: str) -> List[TransactionEvent]:
    """Get all payment transactions for a player, ordered chronologically"""
    events = []

    # Get all transactions where player is payer OR recipient
    transactions = (
        db.query(PaymentTransaction)
        .filter(
            PaymentTransaction.game_id == game_id,
            (
                (PaymentTransaction.payer_id == player_id) |
                (PaymentTransaction.recipient_id == player_id)
            ),
            PaymentTransaction.status == 'completed'
        )
        .order_by(PaymentTransaction.created_at.asc())
        .all()
    )

    for txn in transactions:
        if str(txn.payer_id) == str(player_id):
            # Player is paying someone -> balance increases (they owe less)
            events.append(TransactionEvent(
                timestamp=txn.created_at,
                amount_cents=txn.amount_cents,
                transaction_id=str(txn.id),
                description=f"Paid ${txn.amount_cents/100:.2f}"
            ))
        else:
            # Player is receiving payment -> balance decreases (they are owed less)
            events.append(TransactionEvent(
                timestamp=txn.created_at,
                amount_cents=-txn.amount_cents,
                transaction_id=str(txn.id),
                description=f"Received ${txn.amount_cents/100:.2f}"
            ))

    return events


def get_session_events(db, game_id: str, player_id: str) -> List[TransactionEvent]:
    """Get all session results for a player, ordered chronologically"""
    events = []

    # Get all sessions where player participated
    sessions = (
        db.query(SessionPlayerSummary, Session)
        .join(Session, SessionPlayerSummary.session_id == Session.id)
        .filter(
            Session.game_id == game_id,
            SessionPlayerSummary.player_id == player_id
        )
        .order_by(Session.started_at.asc())
        .all()
    )

    for sps, session in sessions:
        events.append(TransactionEvent(
            timestamp=session.started_at,
            amount_cents=sps.net,
            transaction_id=str(session.id),
            description=f"Session {session.external_id}: ${sps.net/100:.2f}"
        ))

    return events


def find_negative_since_timestamp(
    db,
    game_id: str,
    player_id: str,
    payment_events: List[TransactionEvent]
) -> Optional[datetime]:
    """
    Replay session and payment history to find when balance MOST RECENTLY became negative.

    This tracks the current consecutive period of being negative, NOT the first time ever.
    The timestamp resets each time the balance goes back to >= $0.

    Returns:
        The timestamp when balance most recently went negative, or None if never negative.
    """
    # Get session events (these determine poker winnings)
    session_events = get_session_events(db, game_id, player_id)

    # Combine and sort all events chronologically
    all_events = sorted(
        session_events + payment_events,
        key=lambda e: e.timestamp
    )

    running_balance = 0
    most_recent_negative_timestamp = None
    was_negative = False

    for event in all_events:
        old_balance = running_balance
        running_balance += event.amount_cents

        # Check for transition from non-negative to negative
        if old_balance >= 0 and running_balance < 0:
            # Balance just became negative - record this timestamp
            most_recent_negative_timestamp = event.timestamp
            was_negative = True
        elif old_balance < 0 and running_balance >= 0:
            # Balance just became non-negative - reset the timestamp
            most_recent_negative_timestamp = None
            was_negative = False
        # If still negative, keep the existing timestamp

    # Return the most recent timestamp when balance became negative
    # (will be None if balance is currently non-negative)
    return most_recent_negative_timestamp


def fix_balance_timestamps(game_code: Optional[str] = None, dry_run: bool = True):
    """
    Fix balance_negative_since timestamps for all players with negative balances.

    Args:
        game_code: If provided, only fix this game. Otherwise fix all games.
        dry_run: If True, only show what would change without updating.
    """
    with SessionLocal() as db:
        # Get games to process
        if game_code:
            games = db.query(Game).filter(Game.public_code == game_code).all()
            if not games:
                print(f"ERROR: Game with code '{game_code}' not found")
                return
        else:
            games = db.query(Game).all()

        print(f"\n{'='*80}")
        print(f"Mode: {'DRY RUN (no changes will be made)' if dry_run else 'LIVE UPDATE'}")
        print(f"Games to process: {len(games)}")
        print(f"{'='*80}\n")

        total_updated = 0
        total_skipped = 0

        for game in games:
            print(f"\nProcessing game: {game.title or game.public_code} ({game.public_code})")
            print(f"-" * 80)

            # Get all players with negative balances
            negative_balances = (
                db.query(PaymentBalance, Player)
                .join(Player, PaymentBalance.player_id == Player.id)
                .filter(
                    PaymentBalance.game_id == game.id,
                    PaymentBalance.payment_balance < 0
                )
                .all()
            )

            if not negative_balances:
                print("  No players with negative balances")
                continue

            print(f"  Found {len(negative_balances)} players with negative balances\n")

            for balance, player in negative_balances:
                print(f"  Player: {player.display_name}")
                print(f"    Current balance: ${balance.payment_balance / 100:.2f}")
                print(f"    Current negative_since: {balance.balance_negative_since}")

                # Calculate poker winnings
                poker_winnings = calculate_poker_winnings(db, game.id, player.id)
                print(f"    Poker winnings: ${poker_winnings / 100:.2f}")

                # Get payment events
                payment_events = get_payment_events(db, game.id, player.id)
                print(f"    Payment transactions: {len(payment_events)}")

                # Find when balance first went negative (considers both sessions and payments)
                new_negative_since = find_negative_since_timestamp(db, game.id, player.id, payment_events)

                if new_negative_since:
                    days_negative = (datetime.now(timezone.utc) - new_negative_since).days
                    print(f"    Calculated negative_since: {new_negative_since} ({days_negative} days ago)")
                else:
                    # This should not happen with the new logic that replays sessions
                    print(f"    ERROR: Unable to determine negative_since timestamp!")
                    print(f"           Balance is negative but no history found.")
                    total_skipped += 1
                    continue

                # Decide if we need to update
                should_update = False
                if balance.balance_negative_since is None and new_negative_since is not None:
                    should_update = True
                    print(f"    ACTION: Set timestamp (was NULL)")
                elif balance.balance_negative_since != new_negative_since:
                    should_update = True
                    print(f"    ACTION: Update timestamp (different)")
                else:
                    print(f"    ACTION: Skip (already correct)")
                    total_skipped += 1

                if should_update:
                    if not dry_run:
                        balance.balance_negative_since = new_negative_since
                        total_updated += 1
                        print(f"    ✓ Updated")
                    else:
                        total_updated += 1
                        print(f"    ✓ Would update")

                print()

            if not dry_run:
                db.commit()
                print(f"  Committed changes for game {game.public_code}")

        print(f"\n{'='*80}")
        print(f"Summary:")
        print(f"  Players updated: {total_updated}")
        print(f"  Players skipped (already correct): {total_skipped}")
        print(f"  Total processed: {total_updated + total_skipped}")
        if dry_run:
            print(f"\n  NOTE: This was a dry run. No changes were made.")
            print(f"        Run without --dry-run to apply changes.")
        print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Fix balance_negative_since timestamps by replaying payment history'
    )
    parser.add_argument(
        '--game-code',
        type=str,
        help='Only process this specific game code (e.g., C4QRO)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=False,
        help='Show what would change without making updates'
    )

    args = parser.parse_args()

    try:
        fix_balance_timestamps(
            game_code=args.game_code,
            dry_run=args.dry_run
        )
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
