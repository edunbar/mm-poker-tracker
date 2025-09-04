#!/usr/bin/env python3
"""
Test script to insert a few sample payments to verify the system works.
"""

import os
import sys
from datetime import datetime
from decimal import Decimal

# Add the backend src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from db.database import SessionLocal
from db.models import Game, Player
from services.payment_service import PaymentService


def get_or_create_player(db, name):
    """Get existing player or create new one"""
    player = db.query(Player).filter(Player.display_name == name).first()
    if player:
        return player
    
    print(f"Creating new player: {name}")
    player = Player(display_name=name)
    db.add(player)
    db.flush()
    return player


def main():
    print("Test Payment Seed Script")
    print("=" * 30)
    
    # Get public code from command line or default
    public_code = sys.argv[1] if len(sys.argv) > 1 else "C4QROK"
    print(f"Using public code: {public_code}")
    
    # Initialize payment service
    payment_service = PaymentService()
    
    with SessionLocal() as db:
        # Get the game
        game = db.query(Game).filter(Game.public_code == public_code).first()
        if not game:
            print(f"Error: Game with public code '{public_code}' not found!")
            print("Available games:")
            games = db.query(Game).all()
            for g in games:
                print(f"  - {g.public_code}: {g.title or 'Untitled'}")
            return
        
        print(f"Found game: {game.title or 'Untitled'} ({game.public_code})")
        print()
        
        # Test data - just a few payments
        test_payments = [
            ("4/25/2025", "Tomo", "Grant", "5.12", None, "To Grant"),
            ("4/25/2025", "Eric", "Grant", "60.00", None, "To Grant"),
            ("5/7/2025", "Jack", "Grant", "58.67", "Venmo", "To Grant"),
        ]
        
        for date_str, sender, receiver, amount_str, method, notes in test_payments:
            try:
                # Parse data
                payment_date = datetime.strptime(date_str, '%m/%d/%Y')
                amount = Decimal(amount_str)
                
                # Get or create players
                payer = get_or_create_player(db, sender)
                recipient = get_or_create_player(db, receiver)
                
                # Record payment
                payment = payment_service.record_payment(
                    game_id=str(game.id),
                    payer_id=str(payer.id),
                    recipient_id=str(recipient.id),
                    amount=amount,
                    payment_date=payment_date,
                    payment_method=method,
                    notes=notes,
                    created_by="test_seed"
                )
                
                print(f"✓ {sender} → {receiver}: ${amount} ({date_str})")
                
            except Exception as e:
                print(f"✗ Error: {str(e)}")
        
        db.commit()
        print()
        print("Test payments inserted successfully!")
        print(f"Visit /payments/{public_code} to view the results!")


if __name__ == "__main__":
    main()