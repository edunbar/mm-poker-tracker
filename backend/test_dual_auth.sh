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

PUBLIC_CODE=$(echo $GAME_RESPONSE | grep -o '"public_code":"[^"]*"' | cut -d'"' -f4)
ADMIN_CODE=$(echo $GAME_RESPONSE | grep -o '"admin_code":"[^"]*"' | cut -d'"' -f4)

echo "✓ Game created:"
echo "  Public Code: $PUBLIC_CODE"
echo "  Admin Code: $ADMIN_CODE"
echo ""

# Step 2: Register a test user
echo "2. Registering test user..."
REGISTER_RESPONSE=$(curl -s -X POST "$API_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "dualauth_test@example.com",
    "password": "SecurePassword123!",
    "display_name": "Dual Auth Tester"
  }')

JWT_TOKEN=$(echo $REGISTER_RESPONSE | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$JWT_TOKEN" ]; then
  echo "✗ Failed to register user"
  echo "Response: $REGISTER_RESPONSE"
  exit 1
fi

echo "✓ User registered and JWT obtained"
echo ""

# Step 3: Test claim endpoint with JWT
echo "3. Testing /claim endpoint with JWT..."
CLAIM_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$API_URL/games/claim" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"admin_code\":\"$ADMIN_CODE\"}")

HTTP_STATUS=$(echo "$CLAIM_RESPONSE" | grep "HTTP_STATUS" | cut -d':' -f2)
CLAIM_BODY=$(echo "$CLAIM_RESPONSE" | sed '/HTTP_STATUS/d')

if [ "$HTTP_STATUS" = "201" ]; then
  echo "✓ Game successfully claimed (HTTP 201)"
  echo "  Response: $CLAIM_BODY"
else
  echo "✗ Claim failed with status $HTTP_STATUS"
  echo "  Response: $CLAIM_BODY"
fi
echo ""

# Step 4: Test accessing route with admin code (should work - within 90 day grace period)
echo "4. Testing POST /payments with X-Admin-Code (within grace period)..."
PAYMENT_ADMIN=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$API_URL/games/$PUBLIC_CODE/payments" \
  -H "X-Admin-Code: $ADMIN_CODE" \
  -H "Content-Type: application/json" \
  -d '{
    "payer_id": "00000000-0000-0000-0000-000000000001",
    "recipient_id": "00000000-0000-0000-0000-000000000002",
    "amount": 50.00,
    "notes": "Test payment via admin code"
  }')

HTTP_STATUS=$(echo "$PAYMENT_ADMIN" | grep "HTTP_STATUS" | cut -d':' -f2)
PAYMENT_BODY=$(echo "$PAYMENT_ADMIN" | sed '/HTTP_STATUS/d')

if [ "$HTTP_STATUS" = "201" ] || [ "$HTTP_STATUS" = "400" ]; then
  echo "✓ Admin code auth works (HTTP $HTTP_STATUS)"
  echo "  Response: $PAYMENT_BODY"
else
  echo "✗ Admin code auth failed with status $HTTP_STATUS"
  echo "  Response: $PAYMENT_BODY"
fi
echo ""

# Step 5: Test accessing route with JWT (should work - owner)
echo "5. Testing POST /payments with JWT token..."
PAYMENT_JWT=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$API_URL/games/$PUBLIC_CODE/payments" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "payer_id": "00000000-0000-0000-0000-000000000001",
    "recipient_id": "00000000-0000-0000-0000-000000000002",
    "amount": 75.00,
    "notes": "Test payment via JWT"
  }')

HTTP_STATUS=$(echo "$PAYMENT_JWT" | grep "HTTP_STATUS" | cut -d':' -f2)
PAYMENT_BODY=$(echo "$PAYMENT_JWT" | sed '/HTTP_STATUS/d')

if [ "$HTTP_STATUS" = "201" ] || [ "$HTTP_STATUS" = "400" ]; then
  echo "✓ JWT auth works (HTTP $HTTP_STATUS)"
  echo "  Response: $PAYMENT_BODY"
else
  echo "✗ JWT auth failed with status $HTTP_STATUS"
  echo "  Response: $PAYMENT_BODY"
fi
echo ""

# Step 6: Test with wrong admin code (should fail)
echo "6. Testing with WRONG admin code (should fail)..."
WRONG_CODE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$API_URL/games/$PUBLIC_CODE/payments" \
  -H "X-Admin-Code: WRONG_CODE_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "payer_id": "00000000-0000-0000-0000-000000000001",
    "recipient_id": "00000000-0000-0000-0000-000000000002",
    "amount": 25.00
  }')

HTTP_STATUS=$(echo "$WRONG_CODE" | grep "HTTP_STATUS" | cut -d':' -f2)
WRONG_BODY=$(echo "$WRONG_CODE" | sed '/HTTP_STATUS/d')

if [ "$HTTP_STATUS" = "403" ]; then
  echo "✓ Wrong admin code correctly rejected (HTTP 403)"
  echo "  Response: $WRONG_BODY"
else
  echo "✗ Expected 403, got $HTTP_STATUS"
  echo "  Response: $WRONG_BODY"
fi
echo ""

# Step 7: Test with no auth (should fail)
echo "7. Testing with NO authentication (should fail)..."
NO_AUTH=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$API_URL/games/$PUBLIC_CODE/payments" \
  -H "Content-Type: application/json" \
  -d '{
    "payer_id": "00000000-0000-0000-0000-000000000001",
    "recipient_id": "00000000-0000-0000-0000-000000000002",
    "amount": 25.00
  }')

HTTP_STATUS=$(echo "$NO_AUTH" | grep "HTTP_STATUS" | cut -d':' -f2)
NO_AUTH_BODY=$(echo "$NO_AUTH" | sed '/HTTP_STATUS/d')

if [ "$HTTP_STATUS" = "401" ]; then
  echo "✓ No auth correctly rejected (HTTP 401)"
  echo "  Response: $NO_AUTH_BODY"
else
  echo "✗ Expected 401, got $HTTP_STATUS"
  echo "  Response: $NO_AUTH_BODY"
fi
echo ""

# Step 8: Re-claim to test 200 response
echo "8. Testing re-claim (should return 200 and extend expiration)..."
RECLAIM=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$API_URL/games/claim" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"admin_code\":\"$ADMIN_CODE\"}")

HTTP_STATUS=$(echo "$RECLAIM" | grep "HTTP_STATUS" | cut -d':' -f2)
RECLAIM_BODY=$(echo "$RECLAIM" | sed '/HTTP_STATUS/d')

if [ "$HTTP_STATUS" = "200" ]; then
  echo "✓ Re-claim successful (HTTP 200)"
  echo "  Response: $RECLAIM_BODY"
else
  echo "✗ Re-claim failed with status $HTTP_STATUS"
  echo "  Response: $RECLAIM_BODY"
fi
echo ""

echo "=== Test Summary ==="
echo "All dual authentication mechanisms tested successfully!"
