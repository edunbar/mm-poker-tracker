#!/usr/bin/env python3
"""
Script to clean up duplicate payment entries and recalculate balances.
"""

import sys
import os
from decimal import Decimal
from datetime import datetime

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from db.database import SessionLocal
from sqlalchemy import text
from services.payment_service import PaymentService

def find_and_remove_duplicates():
    """Find and remove duplicate payment entries."""
    
    with SessionLocal() as db:
        print("Finding duplicate payment entries...")
        
        # Find duplicates based on game_id, payer_id, recipient_id, amount_cents, payment_date
        duplicate_query = text("""
            WITH duplicates AS (
                SELECT 
                    id,
                    game_id,
                    payer_id,
                    recipient_id, 
                    amount_cents,
                    payment_date::date as payment_date_only,
                    ROW_NUMBER() OVER (
                        PARTITION BY game_id, payer_id, recipient_id, amount_cents, payment_date::date 
                        ORDER BY created_at ASC
                    ) as row_num
                FROM payment_transactions
            )
            SELECT 
                pt.id,
                p1.display_name as payer_name,
                p2.display_name as recipient_name,
                pt.amount_cents,
                pt.payment_date,
                pt.created_at
            FROM duplicates d
            JOIN payment_transactions pt ON pt.id = d.id
            JOIN players p1 ON p1.id = pt.payer_id  
            JOIN players p2 ON p2.id = pt.recipient_id
            WHERE d.row_num > 1
            ORDER BY pt.created_at DESC
        """)
        
        duplicates = db.execute(duplicate_query).fetchall()
        
        if not duplicates:
            print("No duplicate payments found.")
            return
            
        print(f"Found {len(duplicates)} duplicate payment entries:")
        for dup in duplicates:
            amount_dollars = dup.amount_cents / 100
            print(f"  - {dup.payer_name} → {dup.recipient_name}: ${amount_dollars:.2f} on {dup.payment_date.strftime('%Y-%m-%d')} (ID: {dup.id})")
        
        # Confirm deletion
        print(f"\nWill delete {len(duplicates)} duplicate entries, keeping the earliest created entry for each duplicate set.")
        
        # Delete duplicates
        duplicate_ids = [str(dup.id) for dup in duplicates]
        if duplicate_ids:
            delete_query = text(f"""
                DELETE FROM payment_transactions 
                WHERE id IN ({','.join([f"'{id}'" for id in duplicate_ids])})
            """)
            
            result = db.execute(delete_query)
            db.commit()
            print(f"Deleted {result.rowcount} duplicate payment entries.")
        
        return len(duplicates)

def recalculate_all_balances():
    """Recalculate all payment balances after cleanup."""
    
    with SessionLocal() as db:
        print("\nRecalculating payment balances...")
        
        # Get all games that have payment data
        games_query = text("""
            SELECT DISTINCT g.id, g.public_code
            FROM games g
            WHERE EXISTS (
                SELECT 1 FROM payment_transactions pt WHERE pt.game_id = g.id
            ) OR EXISTS (
                SELECT 1 FROM payment_balances pb WHERE pb.game_id = g.id
            )
        """)
        
        games = db.execute(games_query).fetchall()
        
        payment_service = PaymentService()
        
        for game in games:
            print(f"Recalculating balances for game {game.public_code}...")
            
            # Delete existing balances for this game
            delete_balances_query = text("""
                DELETE FROM payment_balances WHERE game_id = :game_id
            """)
            db.execute(delete_balances_query, {"game_id": game.id})
            
            # Recalculate balances using the service
            try:
                balances = payment_service.get_payment_summary(str(game.id))
                print(f"  - Recalculated balances for {len(balances)} players")
                
                # Show current balances
                for balance in balances:
                    current_balance_dollars = balance.current_balance / 100
                    print(f"    {balance.player_name}: ${current_balance_dollars:+.2f}")
                    
            except Exception as e:
                print(f"  - Error recalculating balances: {e}")
        
        db.commit()
        print("Balance recalculation complete!")

def main():
    print("=== Payment Ledger Cleanup Script ===")
    print("This script will:")
    print("1. Find and remove duplicate payment entries")
    print("2. Recalculate all payment balances")
    print()
    
    try:
        # Remove duplicates
        duplicates_removed = find_and_remove_duplicates()
        
        # Recalculate balances
        recalculate_all_balances()
        
        print("\n=== Cleanup Complete ===")
        if duplicates_removed:
            print(f"Removed {duplicates_removed} duplicate payment entries.")
        print("All payment balances have been recalculated.")
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()