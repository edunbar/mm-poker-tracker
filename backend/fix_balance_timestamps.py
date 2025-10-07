"""
Script to fix balance_negative_since timestamps based on historical payment data.

This reconstructs when each player's balance actually became negative by replaying
their payment transaction history in chronological order.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime, timezone
from db.database import SessionLocal
from db.models import Game, Player, PaymentBalance, PaymentTransaction, SessionPlayerSummary, Session
from sqlalchemy import func

def reconstruct_balance_timestamps(game_public_code: str):
    """
    Reconstruct balance_negative_since for all players in a game.

    For each player:
    1. Get their poker winnings from sessions
    2. Replay all payment transactions in chronological order
    3. Track when balance first becomes negative
    4. Update balance_negative_since to that timestamp
    """
    with SessionLocal() as db:
        # Get the game
        game = db.query(Game).filter(Game.public_code == game_public_code).first()
        if not game:
            print(f"Game {game_public_code} not found")
            return

        print(f"Processing game: {game.title} ({game_public_code})")

        # Get all players in this game
        player_balances = db.query(PaymentBalance).filter(
            PaymentBalance.game_id == game.id
        ).all()

        for balance in player_balances:
            # Get player name
            player = db.query(Player).filter(Player.id == balance.player_id).first()
            player_name = player.display_name if player else "Unknown"

            # Calculate poker net winnings
            poker_winnings = db.query(func.coalesce(func.sum(SessionPlayerSummary.net), 0))\
                .join(Session, SessionPlayerSummary.session_id == Session.id)\
                .filter(
                    Session.game_id == game.id,
                    SessionPlayerSummary.player_id == balance.player_id
                ).scalar() or 0

            # Get all payment transactions involving this player, ordered chronologically
            transactions = db.query(PaymentTransaction).filter(
                PaymentTransaction.game_id == game.id
            ).filter(
                (PaymentTransaction.payer_id == balance.player_id) |
                (PaymentTransaction.recipient_id == balance.player_id)
            ).filter(
                PaymentTransaction.status == 'completed'
            ).order_by(PaymentTransaction.payment_date).all()

            # Replay transaction history to find when balance became negative
            running_balance = poker_winnings  # Start with poker winnings (in cents)
            first_negative_timestamp = None

            for txn in transactions:
                if str(txn.payer_id) == str(balance.player_id):
                    # Player PAID someone - increases their balance
                    running_balance += txn.amount_cents
                else:
                    # Player RECEIVED payment - decreases their balance
                    running_balance -= txn.amount_cents

                # Check if this transaction caused balance to go negative
                if running_balance < 0 and first_negative_timestamp is None:
                    first_negative_timestamp = txn.payment_date
                    break  # Found when they first went negative

            # Update the balance record
            current_balance = balance.payment_balance

            if current_balance < 0:
                # Balance is currently negative
                if first_negative_timestamp:
                    balance.balance_negative_since = first_negative_timestamp
                    days_negative = (datetime.now(timezone.utc) - first_negative_timestamp).days
                    print(f"  {player_name}: Set timestamp to {first_negative_timestamp.date()} ({days_negative} days ago)")
                else:
                    # Balance is negative but no transaction history found
                    # This means they went negative from poker losses alone
                    # We don't have exact timestamp, so leave as NULL or set to NOW
                    print(f"  {player_name}: Negative balance but no payment history - keeping existing timestamp")
            else:
                # Balance is positive or zero - clear timestamp
                if balance.balance_negative_since is not None:
                    balance.balance_negative_since = None
                    print(f"  {player_name}: Balance is positive - cleared timestamp")

        # Commit all changes
        db.commit()
        print(f"\nSuccessfully updated {len(player_balances)} player balances")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_balance_timestamps.py <GAME_PUBLIC_CODE>")
        print("Example: python fix_balance_timestamps.py C4QRO")
        sys.exit(1)

    game_code = sys.argv[1]
    reconstruct_balance_timestamps(game_code)
