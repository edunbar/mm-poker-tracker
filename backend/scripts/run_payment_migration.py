#!/usr/bin/env python3
"""
Manually run the payment tables migration using SQLAlchemy
"""

import os
import sys

# Add the backend src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from db.database import SessionLocal
from sqlalchemy import text

def main():
    print("Running Payment Tables Migration...")
    print("=" * 40)
    
    # Read the SQL file
    sql_file_path = os.path.join(os.path.dirname(__file__), '..', 'create_payment_tables.sql')
    
    with open(sql_file_path, 'r') as f:
        sql_content = f.read()
    
    with SessionLocal() as db:
        try:
            # Execute the SQL
            db.execute(text(sql_content))
            db.commit()
            
            print("✓ Payment tables created successfully!")
            print("✓ Indexes created successfully!")
            print("✓ Migration record added!")
            print()
            print("You can now run the payment seed scripts:")
            print("  python scripts/test_payment_seed.py C4QROK")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            db.rollback()
            return False
    
    return True

if __name__ == "__main__":
    main()