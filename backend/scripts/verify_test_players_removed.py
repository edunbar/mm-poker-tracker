#!/usr/bin/env python3
"""
Script to verify that test players have been completely removed.
"""

import sys
import os

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from db.database import SessionLocal
from sqlalchemy import text

def verify_removal():
    """Verify that test players have been removed."""
    
    test_names = ['alice', 'bob', 'charlie', 'david']
    
    with SessionLocal() as db:
        print("=== Verifying Test Player Removal ===")
        print(f"Checking for players: {', '.join(test_names)}")
        print()
        
        # Check for remaining test players
        find_players_query = text("""
            SELECT id, display_name, external_id, created_at
            FROM players 
            WHERE LOWER(display_name) = ANY(:names)
            ORDER BY display_name
        """)
        
        remaining_players = db.execute(find_players_query, {"names": test_names}).fetchall()
        
        if remaining_players:
            print(f"❌ Found {len(remaining_players)} remaining test players:")
            for player in remaining_players:
                print(f"  - {player.display_name} (ID: {player.id})")
            return False
        else:
            print("✅ No test players found in players table")
        
        # Check for any orphaned payment transactions
        orphan_payments_query = text("""
            SELECT COUNT(*) as count
            FROM payment_transactions pt
            LEFT JOIN players p1 ON p1.id = pt.payer_id
            LEFT JOIN players p2 ON p2.id = pt.recipient_id
            WHERE p1.id IS NULL OR p2.id IS NULL
        """)
        
        orphan_count = db.execute(orphan_payments_query).scalar()
        
        if orphan_count > 0:
            print(f"❌ Found {orphan_count} orphaned payment transactions")
            return False
        else:
            print("✅ No orphaned payment transactions found")
        
        # Check for any orphaned payment balances
        orphan_balances_query = text("""
            SELECT COUNT(*) as count
            FROM payment_balances pb
            LEFT JOIN players p ON p.id = pb.player_id
            WHERE p.id IS NULL
        """)
        
        orphan_balance_count = db.execute(orphan_balances_query).scalar()
        
        if orphan_balance_count > 0:
            print(f"❌ Found {orphan_balance_count} orphaned payment balances")
            return False
        else:
            print("✅ No orphaned payment balances found")
        
        # Check for any orphaned game players
        orphan_game_players_query = text("""
            SELECT COUNT(*) as count
            FROM game_players gp
            LEFT JOIN players p ON p.id = gp.player_id
            WHERE p.id IS NULL
        """)
        
        orphan_game_count = db.execute(orphan_game_players_query).scalar()
        
        if orphan_game_count > 0:
            print(f"❌ Found {orphan_game_count} orphaned game player associations")
            return False
        else:
            print("✅ No orphaned game player associations found")
        
        print()
        print("🎉 All test players and associated data have been successfully removed!")
        return True

def main():
    try:
        success = verify_removal()
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"Error during verification: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()