#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, '/app/src')

from db.database import SessionLocal
from db.models import Game, SessionPlayerSummary, Session, PaymentTransaction, PaymentBalance, Player
from sqlalchemy import func
from datetime import datetime, timezone

def debug_sync():
    with SessionLocal() as db:
        # Get game ID
        game = db.query(Game).filter(Game.public_code == 'C4QRO').first()
        if not game:
            print("Game C4QRO not found!")
            return

        game_id = str(game.id)
        print(f"Game ID: {game_id}")

        # Step 1: Get session players
        session_players = (
            db.query(SessionPlayerSummary.player_id)
            .join(Session, SessionPlayerSummary.session_id == Session.id)
            .filter(Session.game_id == game_id)
            .distinct()
        ).all()

        print(f"\nFound {len(session_players)} session players")

        # Step 2: Get payment players
        payment_players = (
            db.query(PaymentTransaction.payer_id.label('player_id'))
            .filter(PaymentTransaction.game_id == game_id)
            .union(
                db.query(PaymentTransaction.recipient_id.label('player_id'))
                .filter(PaymentTransaction.game_id == game_id)
            )
            .distinct()
        ).all()

        print(f"Found {len(payment_players)} payment players")

        # Step 3: Union them
        session_query = db.query(SessionPlayerSummary.player_id).join(Session, SessionPlayerSummary.session_id == Session.id).filter(Session.game_id == game_id).distinct()
        payment_query = db.query(PaymentTransaction.payer_id.label('player_id')).filter(PaymentTransaction.game_id == game_id).union(db.query(PaymentTransaction.recipient_id.label('player_id')).filter(PaymentTransaction.game_id == game_id)).distinct()

        all_player_ids = session_query.union(payment_query).all()
        player_ids = [str(pid[0]) for pid in all_player_ids]

        print(f"\nTotal unique player IDs: {len(player_ids)}")

        # Check Hunter and Jay specifically
        hunter_id = db.query(Player.id).filter(Player.display_name == 'Hunter').scalar()
        jay_id = db.query(Player.id).filter(Player.display_name == 'Jay').scalar()

        print(f"\nHunter ID: {hunter_id}")
        print(f"Jay ID: {jay_id}")
        print(f"Hunter in player_ids: {str(hunter_id) in player_ids}")
        print(f"Jay in player_ids: {str(jay_id) in player_ids}")

        # Step 4: Test balance calculation for Hunter
        if str(hunter_id) in player_ids:
            print(f"\n=== Testing balance calculation for Hunter ===")
            player_id = str(hunter_id)

            # Calculate poker net winnings
            poker_winnings_result = (
                db.query(func.coalesce(func.sum(SessionPlayerSummary.net), 0))
                .join(Session, SessionPlayerSummary.session_id == Session.id)
                .filter(
                    Session.game_id == game_id,
                    SessionPlayerSummary.player_id == player_id
                )
                .scalar()
            )
            poker_winnings = poker_winnings_result or 0
            print(f"Poker winnings: {poker_winnings}")

            # Calculate total paid
            total_paid = (
                db.query(func.coalesce(func.sum(PaymentTransaction.amount_cents), 0))
                .filter(
                    PaymentTransaction.game_id == game_id,
                    PaymentTransaction.payer_id == player_id,
                    PaymentTransaction.status == 'completed'
                )
                .scalar()
            ) or 0
            print(f"Total paid: {total_paid}")

            # Calculate total received
            total_received = (
                db.query(func.coalesce(func.sum(PaymentTransaction.amount_cents), 0))
                .filter(
                    PaymentTransaction.game_id == game_id,
                    PaymentTransaction.recipient_id == player_id,
                    PaymentTransaction.status == 'completed'
                )
                .scalar()
            ) or 0
            print(f"Total received: {total_received}")

            payment_balance = poker_winnings - total_paid + total_received
            print(f"Payment balance: {payment_balance}")

            # Check if record exists
            existing_balance = (
                db.query(PaymentBalance)
                .filter(
                    PaymentBalance.game_id == game_id,
                    PaymentBalance.player_id == player_id
                )
                .first()
            )
            print(f"Existing balance record: {existing_balance}")

            # Try to create record
            if not existing_balance:
                print("Creating new balance record...")
                try:
                    balance = PaymentBalance(
                        game_id=game_id,
                        player_id=player_id,
                        total_paid=total_paid,
                        total_received=total_received,
                        poker_net_winnings=poker_winnings,
                        payment_balance=payment_balance
                    )
                    db.add(balance)
                    db.flush()  # Test if there are any constraint violations
                    print("Balance record created successfully (not committed)")
                    db.rollback()  # Don't actually commit
                except Exception as e:
                    print(f"Error creating balance record: {e}")
                    db.rollback()

if __name__ == "__main__":
    debug_sync()