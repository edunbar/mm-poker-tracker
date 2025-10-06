# Authentication Implementation - Stage 11 Verification

## Test Cases for Dual Authentication Pattern

### 1. POST /api/games/claim (JWT Only)

**Test Case 1.1: Valid admin code, unclaimed game**
- **Setup**: Game exists with admin_code, no owner
- **Request**: JWT + `{ "admin_code": "valid-code" }`
- **Expected**: `201 Created`
- **Response**:
  ```json
  {
    "message": "Game successfully claimed",
    "game": {
      "id": "uuid",
      "public_code": "ABC123",
      "title": "Game Title",
      "claimed_at": "2025-10-02T...",
      "admin_code_expires_at": "2026-01-02T..."
    }
  }
  ```

**Test Case 1.2: Invalid admin code**
- **Setup**: Admin code doesn't exist
- **Request**: JWT + `{ "admin_code": "invalid-code" }`
- **Expected**: `403 Forbidden`
- **Response**: `{ "error": "Invalid admin code" }`

**Test Case 1.3: Already owned by current user**
- **Setup**: Game already claimed by authenticated user
- **Request**: JWT + `{ "admin_code": "valid-code" }`
- **Expected**: `200 OK`
- **Response**:
  ```json
  {
    "message": "Admin code expiration extended",
    "game": {
      "id": "uuid",
      "public_code": "ABC123",
      "title": "Game Title",
      "admin_code_expires_at": "2026-01-02T..."
    }
  }
  ```

**Test Case 1.4: Already owned by another user**
- **Setup**: Game claimed by different user
- **Request**: JWT + `{ "admin_code": "valid-code" }`
- **Expected**: `409 Conflict`
- **Response**: `{ "error": "Game already claimed by another user" }`

---

### 2. POST /api/games/upload (Dual Auth)

**Test Case 2.1: JWT authentication, user owns game**
- **Setup**: User is authenticated and owns the game
- **Request**: JWT in header + `{ "public_code": "ABC123", ... }`
- **Expected**: `200 OK`
- **Response**: Session ingestion success

**Test Case 2.2: JWT authentication, user doesn't own game**
- **Setup**: User is authenticated but doesn't own the game
- **Request**: JWT in header + `{ "public_code": "ABC123", ... }`
- **Expected**: `403 Forbidden`
- **Response**: `{ "error": "Access denied" }` or similar

**Test Case 2.3: Valid X-Admin-Code header (no JWT)**
- **Setup**: No JWT, valid admin code provided
- **Request**: `X-Admin-Code: valid-code` + `{ "public_code": "ABC123", ... }`
- **Expected**: `200 OK`
- **Response**: Session ingestion success

**Test Case 2.4: Invalid X-Admin-Code header (no JWT)**
- **Setup**: No JWT, invalid admin code provided
- **Request**: `X-Admin-Code: invalid-code` + `{ "public_code": "ABC123", ... }`
- **Expected**: `403 Forbidden`
- **Response**: `{ "error": "Invalid admin code" }` or similar

**Test Case 2.5: No authentication provided**
- **Setup**: No JWT, no X-Admin-Code header
- **Request**: `{ "public_code": "ABC123", ... }`
- **Expected**: `401 Unauthorized`
- **Response**: `{ "error": "Authentication required" }` or similar

---

### 3. GET /api/games/me (JWT Only)

**Test Case 3.1: Valid JWT with owned games**
- **Setup**: User authenticated and owns multiple games
- **Request**: JWT in header
- **Expected**: `200 OK`
- **Response**:
  ```json
  {
    "games": [
      {
        "id": "uuid-1",
        "title": "Game 1",
        "public_code": "ABC123",
        "admin_code_expires_at": "2026-01-02T...",
        "created_at": "2025-10-01T...",
        "session_count": 5
      },
      {
        "id": "uuid-2",
        "title": "Game 2",
        "public_code": "DEF456",
        "admin_code_expires_at": null,
        "created_at": "2025-09-15T...",
        "session_count": 2
      }
    ]
  }
  ```

**Test Case 3.2: Valid JWT with no owned games**
- **Setup**: User authenticated but owns no games
- **Request**: JWT in header
- **Expected**: `200 OK`
- **Response**: `{ "games": [] }`

**Test Case 3.3: No JWT provided**
- **Setup**: No authentication
- **Request**: No JWT header
- **Expected**: `401 Unauthorized`
- **Response**: `{ "error": "Authentication required" }` or similar

---

## Frontend UX Verification

### Session Upload Page
- When authenticated: Show banner "Uploading as: user@example.com"
- When authenticated: Do NOT send X-Admin-Code header
- When not authenticated: Send X-Admin-Code header if available
- On 403 error with JWT: Show "You don't own this game" message

### Payment Ledger Page
- Use apiClient.post() with conditional X-Admin-Code header
- When authenticated: JWT auto-attached, no X-Admin-Code
- When not authenticated: Include X-Admin-Code if available

### My Games Page
- Fetch from GET /api/games/me
- Display table with: title, public code, sessions count, created date
- Empty state: "Claim your first game" button ’ /claim-game

### Claim Game Page
- Single input: admin code
- POST to /api/games/claim
- Handle 201 (first claim) vs 200 (re-claim) differently
- Show appropriate success messages
- On success: redirect to /my-games

---

## Implementation Checklist

- [x] Backend: GET /api/games/me endpoint created
- [x] Frontend: ClaimGamePage.tsx created
- [x] Frontend: MyGamesPage.tsx created
- [x] Frontend: SessionIngestPage.tsx updated with auth UX
- [x] Frontend: PaymentLedgerPage.tsx updated to use apiClient
- [x] Frontend: Header.tsx updated with "My Games" and "Claim Game" links
- [x] Frontend: routes.tsx updated with protected routes
- [x] Test cases documented
