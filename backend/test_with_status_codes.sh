#!/bin/bash

API_URL="http://localhost:8000/api"
echo "=== Dual Auth Test with HTTP Status Codes ==="
echo ""

# Create game and register user
GAME_RESPONSE=$(curl -s -X POST "$API_URL/games/create" -H "Content-Type: application/json" -d '{"title":"Test","stakes":"0.25/0.50"}')
PUBLIC_CODE=$(echo "$GAME_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('public_code', ''))")
ADMIN_CODE=$(echo "$GAME_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('admin_code', ''))")

REGISTER=$(curl -s -X POST "$API_URL/auth/register" -H "Content-Type: application/json" -d '{"email":"statustest@example.com","password":"SecurePassword123!","display_name":"Status Tester"}')
JWT_TOKEN=$(echo "$REGISTER" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))")

echo "Setup: Game=$PUBLIC_CODE, JWT obtained"
echo ""

# Test 1: Claim with JWT
echo "TEST 1: Claim game with JWT"
curl -s -w "HTTP Status: %{http_code}\n" -X POST "$API_URL/games/claim" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"admin_code\":\"$ADMIN_CODE\"}"
echo ""

# Test 2: Upload with admin code
echo "TEST 2: Upload with X-Admin-Code"
curl -s -w "HTTP Status: %{http_code}\n" -X POST "$API_URL/games/upload" \
  -H "X-Admin-Code: $ADMIN_CODE" \
  -H "Content-Type: application/json" \
  -d "{\"public_code\":\"$PUBLIC_CODE\",\"sessionId\":\"test-session-001\",\"game_data\":{}}"
echo ""

# Test 3: Upload with JWT
echo "TEST 3: Upload with JWT Bearer token"
curl -s -w "HTTP Status: %{http_code}\n" -X POST "$API_URL/games/upload" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"public_code\":\"$PUBLIC_CODE\",\"sessionId\":\"test-session-002\",\"game_data\":{}}"
echo ""

# Test 4: Wrong admin code
echo "TEST 4: Upload with WRONG admin code (should be 403)"
curl -s -w "HTTP Status: %{http_code}\n" -X POST "$API_URL/games/upload" \
  -H "X-Admin-Code: WRONG_CODE" \
  -H "Content-Type: application/json" \
  -d "{\"public_code\":\"$PUBLIC_CODE\",\"sessionId\":\"test-session-003\",\"game_data\":{}}"
echo ""

# Test 5: No auth
echo "TEST 5: Upload with NO auth (should be 401)"
curl -s -w "HTTP Status: %{http_code}\n" -X POST "$API_URL/games/upload" \
  -H "Content-Type: application/json" \
  -d "{\"public_code\":\"$PUBLIC_CODE\",\"sessionId\":\"test-session-004\",\"game_data\":{}}"
echo ""

# Test 6: Wrong JWT
echo "TEST 6: Upload with INVALID JWT (should be 401)"
curl -s -w "HTTP Status: %{http_code}\n" -X POST "$API_URL/games/upload" \
  -H "Authorization: Bearer invalid.jwt.token" \
  -H "Content-Type: application/json" \
  -d "{\"public_code\":\"$PUBLIC_CODE\",\"sessionId\":\"test-session-005\",\"game_data\":{}}"
echo ""

# Test 7: Different user's JWT trying to access
echo "TEST 7: Creating second user and trying to access first user's game"
REGISTER2=$(curl -s -X POST "$API_URL/auth/register" -H "Content-Type: application/json" -d '{"email":"unauthorized@example.com","password":"SecurePassword123!","display_name":"Unauthorized User"}')
JWT_TOKEN2=$(echo "$REGISTER2" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))")

curl -s -w "HTTP Status: %{http_code}\n" -X POST "$API_URL/games/upload" \
  -H "Authorization: Bearer $JWT_TOKEN2" \
  -H "Content-Type: application/json" \
  -d "{\"public_code\":\"$PUBLIC_CODE\",\"sessionId\":\"test-session-006\",\"game_data\":{}}"
echo ""

echo "=== Summary ==="
echo "Expected results:"
echo "  Test 1: HTTP 201 (first claim)"
echo "  Test 2: HTTP 200 or 400 (auth passes, may fail on business logic)"
echo "  Test 3: HTTP 200 or 400 (auth passes, may fail on business logic)"
echo "  Test 4: HTTP 403 (wrong admin code)"
echo "  Test 5: HTTP 401 (no auth)"
echo "  Test 6: HTTP 401 (invalid JWT)"
echo "  Test 7: HTTP 403 (not owner)"
