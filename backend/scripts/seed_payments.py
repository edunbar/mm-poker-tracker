#!/usr/bin/env python3
"""
Seed payment transactions from CSV-like data.

This script imports historical payment data into the payment ledger system.
It will create players if they don't exist and record all payment transactions.
"""

import os
import sys
from datetime import datetime
from decimal import Decimal
import csv
import io

# Add the backend src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from db.database import SessionLocal
from db.models import Game, Player
from services.payment_service import PaymentService


# Your payment data as a multi-line string
PAYMENT_DATA = """Transaction Date,Sender,Receiver,Amount Paid,Payment Method,Notes / Context
4/22/2025,Tomo,Grant,$ 56.11,,v1.0 variance
4/22/2025,Eric,Jake,$ 34.59,,v1.0 variance
4/22/2025,Tomo,Max,$ 4.79,,v1.0 variance
4/22/2025,Eric,Sturt,$ 4.11,,v1.0 variance
4/25/2025,Fiona,Grant,$ 20.40,,v1.0 variance
4/25/2025,Tomo,Grant,$ 5.12,,To Grant
4/25/2025,Eric,Grant,$ 60.00,,To Grant
4/28/2025,Tomo,Jack,$ 40.00,,to jack
4/28/2025,Eric,Jake,$ 20.00,,To Jake
4/28/2025,Marshall,Jack,$ 20.00,,to jack
4/30/2025,Luke,Jack,$ 60.00,,to jack
5/2/2025,Sturt,Jack,$ 60.00,,
5/5/2025,Tomo,Jack,$ 4.46,,To Jack
5/6/2025,Max,Luke,$ 60.00,,To Luke
5/7/2025,Jack,Grant,$ 58.67,Venmo,To Grant
5/8/2025,Tomo,Nuck,$ 36.33,Venmo,To Nuck
5/11/2025,Tomo,Eric,$ 72.20,Venmo,To Derik 
5/16/2025,Sturt,Tomo,$ 40.00,Venmo,To Tomo
5/23/2025,Jack,Max,$ 220.00,Zelle,To Max
5/23/2025,Tomo,Sturt,$ 63.16,Venmo,To Sturt
5/29/2025,Fiona,Sturt,$ 64.29,Venmo,To Mr. Business
5/29/2025,Tomo,Rex,$ 1.62,Venmo,To Rex
5/29/2025,Tomo,Nuck,$ 116.75,Venmo,To Nuck
5/29/2025,OV,Tomo,$ 40.00,Venmo,To Thomo
5/29/2025,Tomo,Jake,$ 40.00,Venmo,To Jake
5/29/2025,Birday,Tomo,$ 60.00,Venmo,To Thomo
5/29/2025,Tomo,Sturt,$ 60.00,Venmo,To sturt
5/29/2025,Eric,Sturt,$ 61.83,Venmo,To Sturt
5/29/2025,Eric,Jake,$ 4.47,Venmo,To Jake
5/29/2025,Eric,Nuck,$ 87.75,Venmo,To Nuck
5/29/2025,Tomo,Grant,$ 40.00,Venmo,To Grant
6/3/2025,Nuck,Tomo,$ 60.00,venmo,to thomo
6/3/2025,Sturt,Tomo,$ 40.00,venmo,to thomo
6/4/2025,Andrew,Grant,$ 100.00,,to grant
6/11/2025,Jack,Eric,$ 33.57,Venmo,
6/11/2025,Jack,Fiona,$ 7.86,Venmo,
6/26/2025,Max,Eric,$ 261.77,Apple Cash,
7/6/2025,Luke,Tomo,$ 5.00,Venmo,
7/7/2025,Tomo,Jack,$ 72.31,,
7/7/2025,Tomo,Birday,$ 81.44,Venmo,
7/7/2025,Tomo,Eric,$ 49.59,Venmo,
7/9/2025,Sturt,Jack,$ 200.00,venmo,
7/9/2025,Fiona,Grant,$ 80.00,venmo,
7/9/2025,Zack,Tomo,$ 127.99,Zelle,
7/9/2025,Tomo,Andrew,$ 127.99,Venmo,
7/9/2025,Max,Tomo,$ 148.39,Apple Cash,
7/9/2025,Tomo,Andrew,$ 148.39,venmo,
7/9/2025,Nuck,Tomo,$ 5.00,venmo,
7/9/2025,Jake,Tomo,$ 20.00,venmo,
7/9/2025,Tomo,Andrew,$ 20.00,venmo,
7/9/2025,Cade,Tomo,$ 109.10,venmo,
7/9/2025,Tomo,Andrew,$ 109.10,venmo,
7/9/2025,Griff,Tomo,$ 120.00,Zelle,
7/9/2025,Tomo,Andrew,$ 106.22,venmo,
7/9/2025,Tomo,Nuck,$ 13.78,venmo,
7/9/2025,Sturt,Tomo,$ 78.64,venmo,
7/9/2025,Tomo,Grant,$ 71.76,venmo,
7/9/2025,Tomo,Nuck,$ 5.93,venmo,
7/9/2025,Remy,Tomo,$ 166.53,apple cash,
7/10/2025,Tomo,Eric,$ 81.57,venmo,
7/10/2025,Tomo,Eric,$ 37.67,venmo,
7/10/2025,Tomo,Casey,$ 36.66,venmo,
7/10/2025,Luke,Tomo,$ 49.33,venmo,
7/10/2025,Tomo,Casey,$ 43.70,venmo,
7/10/2025,Tomo,Max,$ 55.14,apple cash,
7/10/2025,Tomo,Sturt,$ 39.82,venmo,
7/10/2025,Tomo,Eric,$ 39.23,venmo,
7/10/2025,Eric,Tomo,$ 81.57,venmo,
7/10/2025,Tomo,Jack,$ 81.57,venmo,
7/14/2025,Sturt,Max,$ 120.00,zelle,
7/15/2025,Zack,Tomo,$ 174.29,zelle,
7/15/2025,Tomo,Eric,$ 162.23,Venmo,
7/15/2025,Tomo,Max,$ 80.88,Apple cash,
7/16/2025,Casey,Zack,$ 50.00,zelle,
7/17/2025,Casey,Fiona,$ 8.44,Venmo,
7/17/2025,Casey,Cade,$ 9.82,Venmo,
7/17/2025,Casey,Marshall,$ 17.89,Venmo,
7/17/2025,Casey,Trevor,$ 41.80,Venmo,
7/17/2025,Casey,Max,$ 60.21,Zelle,
7/17/2025,Tomo,Casey,$ 6.22,Venmo,
7/21/2025,Jack,Casey,$ 119.40,Venmo,
7/21/2025,Jack,Jake,$ 27.66,Venmo,
7/21/2025,Jack,Jake,$ 0.09,Venmo,
7/28/2025,Griff,Zack,$ 209.91,Zelle,
7/28/2025,Tomo,Jack,$ 266.47,Venmo,
7/28/2025,Griff,Grant,$ 178.20,Zelle,
7/28/2025,Griff,Jack,$ 151.65,Zelle,
7/29/2025,Grant,Zack,$ 120.00,Zelle,
7/29/2025,Tomo,Trevor,$ 200.00,Venmo,
7/30/2025,Tomo,Jack,$ 100.00,Venmo,
7/30/2025,Tomo,Trevor,$ 100.00,Venmo,
7/30/2025,Casey,Zack,$ 172.77,Zelle,
7/30/2025,Casey,Trevor,$ 227.00,Venmo,
8/5/2025,Trevor,Nuck,$ 264.70,?,
8/6/2025,Grant,Jack,$ 280.00,Venmo,
8/8/2025,Max,Zack,$ 500.00,Zelle,
8/15/2025,Casey,Tomo,$ 308.64,Venmo,
8/18/2025,Sturt,Tomo,$ 69.19,Venmo,
8/18/2025,Trevor,Tomo,$ 195.38,Venmo,
8/20/2025,Dylan,Trevor,$ 40.00,Venmo,"""


def parse_amount(amount_str):
    """Parse amount string like '$ 56.11' into Decimal"""
    # Remove $ and spaces, convert to Decimal
    clean_amount = amount_str.replace('$', '').strip()
    return Decimal(clean_amount)


def parse_date(date_str):
    """Parse date string like '4/22/2025' into datetime"""
    # Handle both M/D/YYYY and MM/DD/YYYY formats
    return datetime.strptime(date_str, '%m/%d/%Y')


def get_or_create_player(db, name):
    """Get existing player or create new one"""
    # Normalize name (strip whitespace, handle case)
    name = name.strip()
    
    # First try exact match
    player = db.query(Player).filter(Player.display_name == name).first()
    if player:
        return player
    
    # Try case-insensitive match
    player = db.query(Player).filter(Player.display_name.ilike(name)).first()
    if player:
        return player
    
    # Create new player
    print(f"Creating new player: {name}")
    player = Player(display_name=name)
    db.add(player)
    db.flush()  # Get the ID
    return player


def main():
    print("Payment Data Import Script")
    print("=" * 50)
    
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
            sys.exit(1)
        
        print(f"Found game: {game.title or 'Untitled'} ({game.public_code})")
        print()
        
        # Parse CSV data
        csv_reader = csv.DictReader(io.StringIO(PAYMENT_DATA))
        
        success_count = 0
        error_count = 0
        
        for row_num, row in enumerate(csv_reader, 1):
            try:
                # Parse row data
                date_str = row['Transaction Date'].strip()
                sender_name = row['Sender'].strip()
                receiver_name = row['Receiver'].strip()
                amount_str = row['Amount Paid'].strip()
                payment_method = row['Payment Method'].strip() or None
                notes = row['Notes / Context'].strip() or None
                
                # Skip empty rows
                if not date_str or not sender_name or not receiver_name or not amount_str:
                    print(f"Row {row_num}: Skipping empty row")
                    continue
                
                # Parse data
                payment_date = parse_date(date_str)
                amount = parse_amount(amount_str)
                
                # Get or create players
                payer = get_or_create_player(db, sender_name)
                recipient = get_or_create_player(db, receiver_name)
                
                # Check if payer and recipient are the same
                if payer.id == recipient.id:
                    print(f"Row {row_num}: ERROR - Payer and recipient are the same: {sender_name}")
                    error_count += 1
                    continue
                
                # Record payment
                payment = payment_service.record_payment(
                    game_id=str(game.id),
                    payer_id=str(payer.id),
                    recipient_id=str(recipient.id),
                    amount=amount,
                    payment_date=payment_date,
                    payment_method=payment_method,
                    notes=notes,
                    created_by="seed_script"
                )
                
                print(f"Row {row_num}: ✓ {sender_name} → {receiver_name}: ${amount} ({payment_date.strftime('%m/%d/%Y')})")
                success_count += 1
                
            except Exception as e:
                print(f"Row {row_num}: ERROR - {str(e)}")
                print(f"  Data: {row}")
                error_count += 1
                continue
        
        db.commit()
        
        print()
        print("=" * 50)
        print("Import Summary:")
        print(f"✓ Successful imports: {success_count}")
        print(f"✗ Failed imports: {error_count}")
        print(f"Total rows processed: {success_count + error_count}")
        
        if success_count > 0:
            print()
            print("Payment summary has been updated automatically.")
            print(f"Visit /payments/{public_code} to view the results!")


if __name__ == "__main__":
    main()