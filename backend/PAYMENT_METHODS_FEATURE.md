# Payment Methods Feature

## Overview
Global player payment methods system allowing players to manage their preferred payment addresses across all games.

## Database Schema

### Table: `player_payment_methods`
```sql
CREATE TABLE player_payment_methods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    payment_method TEXT NOT NULL,  -- e.g., "Venmo", "Zelle", "Apple Cash"
    payment_address TEXT NOT NULL,  -- e.g., "@venmo_handle", "phone", "email"
    is_primary BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_payment_methods_player ON player_payment_methods (player_id);

-- Partial unique index: Only ONE primary per player allowed
CREATE UNIQUE INDEX idx_one_primary_per_player
ON player_payment_methods (player_id)
WHERE is_primary = true;
```

**Migration:** `1d1dbe4025c5_add_player_payment_methods_table.py`

## Key Design Decisions

1. **GLOBAL per player** - NOT per-game
   - A player's Venmo handle is the same across all games
   - No `game_id` column in the table

2. **Multiple methods allowed**
   - Players can have multiple Venmo accounts, multiple Zelle numbers, etc.
   - No uniqueness constraint on payment_method + payment_address

3. **Single primary enforcement**
   - Only ONE method can be marked as primary across ALL their methods
   - Enforced by partial unique index at database level
   - Service layer uses atomic operations to prevent race conditions

4. **Public access**
   - No admin authentication required
   - Any user can view/edit payment methods

5. **Basic validation**
   - Trim whitespace
   - Auto-add @ to Venmo handles if missing
   - Reject empty addresses

## API Endpoints

All routes are registered under `/api/games` blueprint:

### 1. Get all payment methods for a game
```
GET /api/games/<public_code>/all-payment-methods
```
Returns all players in the game with their payment methods.

**Response:**
```json
[
  {
    "player_id": "uuid",
    "player_name": "John Doe",
    "methods": [
      {
        "id": "uuid",
        "payment_method": "Venmo",
        "payment_address": "@john_venmo",
        "is_primary": true,
        "created_at": "2025-10-07T...",
        "updated_at": "2025-10-07T..."
      }
    ]
  }
]
```

### 2. Add payment method
```
POST /api/games/players/<player_id>/payment-methods
Content-Type: application/json

{
  "payment_method": "Venmo",
  "payment_address": "john_venmo",
  "is_primary": true
}
```

**Response:** 201 Created
```json
{
  "id": "uuid",
  "player_id": "uuid",
  "payment_method": "Venmo",
  "payment_address": "@john_venmo",  // Auto-added @
  "is_primary": true,
  "created_at": "2025-10-07T...",
  "updated_at": "2025-10-07T..."
}
```

### 3. Update payment method
```
PUT /api/games/players/<player_id>/payment-methods/<method_id>
Content-Type: application/json

{
  "payment_address": "@new_handle",
  "is_primary": true
}
```

**Response:** 200 OK (same structure as add)

### 4. Set method as primary
```
POST /api/games/players/<player_id>/payment-methods/<method_id>/set-primary
```

Atomically sets this method as primary and unsets all others.

**Response:** 200 OK (same structure as add)

### 5. Delete payment method
```
DELETE /api/games/players/<player_id>/payment-methods/<method_id>
```

**Response:** 204 No Content

## Service Layer

**File:** `src/services/player_payment_method_service.py`

**Class:** `PlayerPaymentMethodService`

### Key Methods

- `get_all_payment_methods_for_game(game_id)` - Get all players' methods for a game
- `get_player_payment_methods(player_id)` - Get one player's methods
- `add_payment_method(player_id, payment_method, payment_address, is_primary)` - Add new method
- `update_payment_method(method_id, ...)` - Update existing method
- `set_primary(method_id)` - Atomically set as primary
- `delete_payment_method(method_id)` - Delete a method
- `_validate_and_clean_address(payment_method, payment_address)` - Validation logic
- `_unset_all_primaries(player_id)` - Helper for atomic primary-setting

### Atomic Primary Setting

When setting a method as primary:
1. Call `_unset_all_primaries(player_id)` to set all methods' `is_primary = False`
2. Set the target method's `is_primary = True`
3. All within the same database transaction

This prevents race conditions where multiple methods could be marked as primary.

## Frontend Integration

**File:** `/Users/ericdunbar/Developer/mmpt-clean/frontend/src/features/payment/pages/PaymentLedgerPage.tsx`

### New Tab: "Payment Methods"

Located next to "Session History" and "Transactions" tabs.

### Features

1. **Player cards** - One card per player in the game
2. **Add Method button** - Opens modal to add new payment method
3. **Method display** - Shows all methods with:
   - Star icon (⭐) for primary method
   - Edit button
   - Delete button
   - Set Primary button (if not already primary)
4. **Modals:**
   - Add/Edit Payment Method modal with form
   - Delete confirmation modal

### API Calls

All frontend API calls use the `/api/games/players/...` prefix (NOT `/api/players/...`).

**Example:**
```typescript
const response = await axios.post(
  `${API_BASE_URL}/api/games/players/${playerId}/payment-methods`,
  { payment_method, payment_address, is_primary }
);
```

## Testing

### Automated API Test

**File:** `backend/test_payment_methods_api.py`

Comprehensive test script that verifies:
1. Get all payment methods (empty)
2. Add first payment method (Venmo, primary)
3. Update payment address
4. Add second payment method (Zelle, not primary)
5. Set second method as primary (should unset first)
6. Verify both methods exist with correct primary status
7. Delete first method
8. Verify only second method remains

**Run test:**
```bash
cd backend
python test_payment_methods_api.py
```

**Sample output:**
```
✓ Created/found game: TEST01
✓ Created/found player: Test Player
✓ ALL TESTS COMPLETED
```

### Manual Testing Checklist

- [ ] Add payment method with Venmo handle without @ (should auto-add)
- [ ] Add payment method with Venmo handle with @ (should not duplicate)
- [ ] Set method as primary (should unset other primaries)
- [ ] Update payment address
- [ ] Delete payment method
- [ ] Verify only one primary per player at all times
- [ ] Test with multiple players in same game
- [ ] Verify payment methods are global (same player across games sees same methods)

## Error Handling

### Validation Errors (400 Bad Request)
- Empty payment address after trimming
- Missing required fields (`payment_method`, `payment_address`)

### Not Found Errors (404 Not Found)
- Player not found
- Payment method not found
- Game not found (for `all-payment-methods` endpoint)

### Database Constraint Violations (500)
- Should never happen due to atomic primary-setting logic
- If partial unique index violated, indicates race condition bug

## Future Enhancements

1. **Payment method types dropdown** - Predefined list (Venmo, Zelle, Apple Cash, PayPal, etc.)
2. **Address format validation** - Email regex for PayPal, phone format for Zelle, etc.
3. **Auto-detection** - Detect payment method type from address format
4. **Payment integration** - Direct links to payment apps with pre-filled amounts
5. **Privacy controls** - Allow players to hide payment methods from certain games
6. **Verification** - Verify payment addresses via test transaction
7. **Preferred currency** - Support multiple currencies per player

## Notes

- The feature is fully implemented and tested
- Backend routes are registered under `/api/games` blueprint
- Frontend correctly uses `/api/games/players/...` URLs
- Database migration has been applied
- Atomic primary-setting prevents race conditions
- Auto-@ addition for Venmo handles works correctly
- All CRUD operations tested and verified
