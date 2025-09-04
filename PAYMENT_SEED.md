# Payment Data Seeding Instructions

I've created scripts to import your historical payment data into the payment ledger system.

## Files Created

1. **`backend/scripts/test_payment_seed.py`** - Test script with 3 sample payments
2. **`backend/scripts/seed_payments.py`** - Full script with all 87 payment transactions

## Prerequisites

1. **Run the database migration first:**
   ```bash
   cd backend
   python -m alembic upgrade head
   ```

2. **Make sure you have a game with public code** (default is `C4QROK`)

## Usage

### Test First (Recommended)

Run the test script to verify everything works:

```bash
cd backend
python scripts/test_payment_seed.py [PUBLIC_CODE]
```

Example:
```bash
python scripts/test_payment_seed.py C4QROK
```

This will insert 3 sample payments and create players if they don't exist.

### Import All Data

Once the test works, run the full import:

```bash
cd backend  
python scripts/seed_payments.py [PUBLIC_CODE]
```

Example:
```bash
python scripts/seed_payments.py C4QROK
```

This will import all 87 payment transactions from your data.

## What the Script Does

1. **Creates missing players** - Any name not found in the database gets added
2. **Parses payment data** - Converts dates, amounts, and payment methods
3. **Records transactions** - Uses your PaymentService to properly record each payment
4. **Updates balances** - Automatically calculates and updates player balances
5. **Provides feedback** - Shows progress and any errors during import

## Expected Output

```
Payment Data Import Script
==================================================
Using public code: C4QROK
Found game: Meow Meow (C4QROK)

Creating new player: Tomo
Creating new player: Grant
Row 1: ✓ Tomo → Grant: $56.11 (04/22/2025)
Row 2: ✓ Eric → Jake: $34.59 (04/22/2025)
...

==================================================
Import Summary:
✓ Successful imports: 87
✗ Failed imports: 0
Total rows processed: 87

Payment summary has been updated automatically.
Visit /payments/C4QROK to view the results!
```

## After Import

1. **Visit the payment ledger** - Navigate to `/payments/C4QROK` (or your public code)
2. **Check balances** - View the "Balance Summary" tab
3. **See settlements** - Check "Settlement Suggestions" for optimal payments
4. **Review history** - Browse "Payment History" to see all imported transactions

## Player Name Matching

The script handles player names intelligently:

- **Exact matches** - "Tomo" matches "Tomo"
- **Case insensitive** - "tomo" matches "Tomo"  
- **Creates new players** - Unknown names get added automatically

## Troubleshooting

- **"Game not found"** - Make sure your public code is correct
- **"Module not found"** - Make sure you're running from the `backend` directory
- **Database errors** - Make sure the migration ran successfully

Your data includes payments from April through August 2025 with various methods (Venmo, Zelle, Apple Cash, etc.) and will give you a comprehensive payment ledger to work with!