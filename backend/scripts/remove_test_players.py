#!/usr/bin/env python3
"""
Script to remove test players (alice, bob, charlie, david) from the payment ledger.
This will clean up all payment-related data for these test players.
"""

import sys
import os

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from db.database import SessionLocal
from sqlalchemy import text

def remove_test_players():
    """Remove test players and all their payment-related data."""
    
    test_names = ['alice', 'bob', 'charlie', 'david']
    
    with SessionLocal() as db:
        print("=== Removing Test Players from Payment Ledger ===")
        print(f"Looking for players: {', '.join(test_names)}")
        print()
        
        # Find test players
        find_players_query = text("""
            SELECT id, display_name, external_id, created_at
            FROM players 
            WHERE LOWER(display_name) = ANY(:names)
            ORDER BY display_name
        """)
        
        test_players = db.execute(find_players_query, {"names": test_names}).fetchall()
        
        if not test_players:
            print("No test players found in the database.")
            return
        
        print(f"Found {len(test_players)} test players:")
        for player in test_players:
            print(f"  - {player.display_name} (ID: {player.id}, External ID: {player.external_id})")
        print()
        
        # Get player IDs
        player_ids = [str(player.id) for player in test_players]
        
        # Check for payment transactions
        payment_check_query = text("""
            SELECT COUNT(*) as count
            FROM payment_transactions 
            WHERE payer_id::text = ANY(:player_ids) OR recipient_id::text = ANY(:player_ids)
        """)
        
        payment_count = db.execute(payment_check_query, {"player_ids": player_ids}).scalar()
        
        # Check for payment balances
        balance_check_query = text("""
            SELECT COUNT(*) as count
            FROM payment_balances 
            WHERE player_id::text = ANY(:player_ids)
        """)
        
        balance_count = db.execute(balance_check_query, {"player_ids": player_ids}).scalar()
        
        # Check for game associations
        game_check_query = text("""
            SELECT COUNT(*) as count
            FROM game_players 
            WHERE player_id::text = ANY(:player_ids)
        """)
        
        game_count = db.execute(game_check_query, {"player_ids": player_ids}).scalar()
        
        # Check for session summaries
        summary_check_query = text("""
            SELECT COUNT(*) as count
            FROM session_player_summaries 
            WHERE player_id::text = ANY(:player_ids)
        """)
        
        summary_count = db.execute(summary_check_query, {"player_ids": player_ids}).scalar()
        
        print("Data to be removed:")
        print(f"  - Payment transactions: {payment_count}")
        print(f"  - Payment balances: {balance_count}")
        print(f"  - Game associations: {game_count}")
        print(f"  - Session summaries: {summary_count}")
        print()
        
        if payment_count + balance_count + game_count + summary_count == 0:
            print("No associated data found. Only removing player records.")
        
        # Proceed with deletion automatically
        print("Proceeding with deletion...")
        
        print("\nRemoving data...")
        
        # Delete in order to respect foreign key constraints
        # 1. Payment transactions (these will be deleted by cascade when players are deleted)
        # 2. Payment balances (these will be deleted by cascade when players are deleted)
        # 3. Session player summaries (these will be deleted by cascade when players are deleted)
        # 4. Game players (these will be deleted by cascade when players are deleted)
        # 5. Players (this will cascade delete everything else)
        
        # Since we have cascade="all, delete-orphan" set up in the models,
        # we just need to delete the players and everything else will be cleaned up
        
        delete_players_query = text("""
            DELETE FROM players 
            WHERE id::text = ANY(:player_ids)
        """)
        
        result = db.execute(delete_players_query, {"player_ids": player_ids})
        db.commit()
        
        print(f"Successfully removed {result.rowcount} test players and all associated data.")
        print("\nCleanup complete!")

def main():
    try:
        remove_test_players()
    except Exception as e:
        print(f"Error during cleanup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()