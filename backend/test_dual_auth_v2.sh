#!/bin/bash

API_URL="http://localhost:8000/api"
echo "=== Testing Dual Authentication System ==="
echo ""

# Step 1: Create a test game
echo "1. Creating test game..."
GAME_RESPONSE=$(curl -s -X POST "$API_URL/games/create" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Game for Dual Auth",
    "stakes": "0.25/0.50"
  }')

PUBLIC_CODE=$(echo "$GAME_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('public_code', ''))")
ADMIN_CODE=$(echo "$GAME_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('admin_code', ''))")

echo "✓ Game created:"
echo "  Public Code: $PUBLIC_CODE"
echo "  Admin Code: $ADMIN_CODE"
echo ""

# Step 2: Register a test user
echo "2. Registering test user..."
REGISTER_RESPONSE=$(curl -s -X POST "$API_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "dualauth_test_v2@example.com",
    "password": "SecurePassword123!",
    "display_name": "Dual Auth Tester V2"
  }')

JWT_TOKEN=$(echo "$REGISTER_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))")

if [ -z "$JWT_TOKEN" ]; then
  echo "✗ Failed to register user"
  echo "Response: $REGISTER_RESPONSE"
  exit 1
fi

echo "✓ User registered and JWT obtained"
echo ""

# Step 3: Test claim endpoint with JWT
echo "3. Testing /claim endpoint with JWT..."
CLAIM_RESPONSE=$(curl -s -X POST "$API_URL/games/claim" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"admin_code\":\"$ADMIN_CODE\"}")

echo "Response: $CLAIM_RESPONSE"
echo ""

# Step 4: Test accessing route with admin code
echo "4. Testing route with X-Admin-Code..."
PAYMENT_ADMIN=$(curl -s -X POST "$API_URL/games/$PUBLIC_CODE/payments" \
  -H "X-Admin-Code: $ADMIN_CODE" \
  -H "Content-Type: application/json" \
  -d '{
    "payer_id": "00000000-0000-0000-0000-000000000001",
    "recipient_id": "00000000-0000-0000-0000-000000000002",
    "amount": 50.00,
    "notes": "Test payment via admin code"
  }')

echo "Response: $PAYMENT_ADMIN"
echo ""

# Step 5: Test accessing route with JWT
echo "5. Testing route with JWT token..."
PAYMENT_JWT=$(curl -s -X POST "$API_URL/games/$PUBLIC_CODE/payments" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "payer_id": "00000000-0000-0000-0000-000000000001",
    "recipient_id": "00000000-0000-0000-0000-000000000002",
    "amount": 75.00,
    "notes": "Test payment via JWT"
  }')

echo "Response: $PAYMENT_JWT"
echo ""

# Step 6: Test with wrong admin code
echo "6. Testing with WRONG admin code (should fail with 403)..."
WRONG_CODE=$(curl -s -X POST "$API_URL/games/$PUBLIC_CODE/payments" \
  -H "X-Admin-Code: WRONG_CODE_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "payer_id": "00000000-0000-0000-0000-000000000001",
    "recipient_id": "00000000-0000-0000-0000-000000000002",
    "amount": 25.00
  }')

echo "Response: $WRONG_CODE"
echo ""

# Step 7: Test with no auth
echo "7. Testing with NO authentication (should fail with 401)..."
NO_AUTH=$(curl -s -X POST "$API_URL/games/$PUBLIC_CODE/payments" \
  -H "Content-Type: application/json" \
  -d '{
    "payer_id": "00000000-0000-0000-0000-000000000001",
    "recipient_id": "00000000-0000-0000-0000-000000000002",
    "amount": 25.00
  }')

echo "Response: $NO_AUTH"
echo ""

# Step 8: Re-claim to test 200 response
echo "8. Testing re-claim (should return 200)..."
RECLAIM=$(curl -s -X POST "$API_URL/games/claim" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"admin_code\":\"$ADMIN_CODE\"}")

echo "Response: $RECLAIM"
echo ""

echo "=== Test Complete ==="
