#!/usr/bin/env python3
"""
Clean up orphaned payment balances for players with no session activity.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from db.database import SessionLocal
from db.models import PaymentBalance, SessionPlayerSummary, Session
from sqlalchemy import select

def cleanup_orphaned_balances():
    with SessionLocal() as db:
        # Find all payment balances
        balances = db.query(PaymentBalance).all()
        
        deleted_count = 0
        for balance in balances:
            # Check if player has any session activity in this game
            has_activity = db.query(SessionPlayerSummary).join(
                Session, SessionPlayerSummary.session_id == Session.id
            ).filter(
                Session.game_id == balance.game_id,
                SessionPlayerSummary.player_id == balance.player_id
            ).count() > 0
            
            if not has_activity:
                print(f"Deleting orphaned balance for player {balance.player_id} in game {balance.game_id}")
                db.delete(balance)
                deleted_count += 1
        
        if deleted_count > 0:
            db.commit()
            print(f"\n✓ Deleted {deleted_count} orphaned payment balance(s)")
        else:
            print("✓ No orphaned payment balances found")

if __name__ == "__main__":
    cleanup_orphaned_balances()
