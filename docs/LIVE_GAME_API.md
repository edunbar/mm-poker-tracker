# Live Game API Documentation

## Overview

The Live Game API enables real-time poker game management with buy-ins, cash-outs, and transaction approval flows. All endpoints use RESTful conventions with JSON request/response bodies.

**Base URL**: `https://homegame.gg/api` (production) or `http://localhost:8000/api` (development)

**Version**: 1.0.0

---

## Authentication

All Live Game endpoints (except SSE stream) require JWT authentication via the `Authorization` header:

```http
Authorization: Bearer <jwt_token>
```

### Obtaining a JWT Token

**Endpoint**: `POST /api/auth/login`

**Request**:
```json
{
  "email": "player@example.com",
  "password": "securepassword123"
}
```

**Response**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "user-uuid",
    "email": "player@example.com",
    "display_name": "Player 1"
  }
}
```

### SSE Authentication

The SSE stream endpoint uses a query parameter for authentication (EventSource API limitation):

```http
GET /api/live-games/{join_code}/stream?token=<jwt_token>
```

**Security Note**: Tokens in URLs may be logged by proxies/load balancers. Use HTTPS in production.

---

## Endpoints

### 1. Create Live Game

Create a new live game session linked to an existing poker game.

**Endpoint**: `POST /api/live-games`

**Authentication**: Required (must have access to the game)

**Request Body**:
```json
{
  "game_id": "uuid-of-existing-game",
  "min_buy_in": 20.00,
  "max_buy_in": 200.00,
  "small_blind": 0.25,
  "big_blind": 0.50
}
```

**Request Schema**:
| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `game_id` | string (UUID) | Yes | Must be a valid game UUID | The parent game to link this live game to |
| `min_buy_in` | number | Yes | > 0 | Minimum buy-in amount in dollars |
| `max_buy_in` | number | No | > min_buy_in | Maximum buy-in amount in dollars (null = no limit) |
| `small_blind` | number | No | > 0 | Small blind amount (reference only) |
| `big_blind` | number | No | > small_blind | Big blind amount (reference only) |

**Response** (201 Created):
```json
{
  "id": "live-game-uuid",
  "game_id": "game-uuid",
  "join_code": "A7X2",
  "status": "active",
  "min_buy_in": 20.00,
  "max_buy_in": 200.00,
  "small_blind": 0.25,
  "big_blind": 0.50,
  "created_at": "2025-01-15T10:30:00Z",
  "created_by_user_id": "user-uuid"
}
```

**Error Responses**:

| Status | Error Code | Description |
|--------|------------|-------------|
| 400 | `INVALID_MIN_BUY_IN` | min_buy_in must be greater than 0 |
| 400 | `INVALID_MAX_BUY_IN` | max_buy_in must be greater than min_buy_in |
| 400 | `ACTIVE_GAME_EXISTS` | Game already has an active live game |
| 404 | `GAME_NOT_FOUND` | game_id does not exist |
| 401 | `UNAUTHORIZED` | Missing or invalid JWT token |

**Example**:
```bash
curl -X POST https://homegame.gg/api/live-games \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "game_id": "550e8400-e29b-41d4-a716-446655440000",
    "min_buy_in": 20.00,
    "max_buy_in": 200.00,
    "small_blind": 0.25,
    "big_blind": 0.50
  }'
```

---

### 2. Get Live Game Info

Retrieve details about a live game by its join code.

**Endpoint**: `GET /api/live-games/{join_code}`

**Authentication**: Required

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `join_code` | string | 4-character join code (e.g., "A7X2") |

**Response** (200 OK):
```json
{
  "id": "live-game-uuid",
  "game_id": "game-uuid",
  "join_code": "A7X2",
  "status": "active",
  "min_buy_in": 20.00,
  "max_buy_in": 200.00,
  "small_blind": 0.25,
  "big_blind": 0.50,
  "created_at": "2025-01-15T10:30:00Z",
  "closed_at": null,
  "created_by_user_id": "user-uuid"
}
```

**Error Responses**:

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `LIVE_GAME_NOT_FOUND` | Join code does not match any active/closed live game |
| 401 | `UNAUTHORIZED` | Missing or invalid JWT token |

**Example**:
```bash
curl -X GET https://homegame.gg/api/live-games/A7X2 \
  -H "Authorization: Bearer <token>"
```

---

### 3. Join Live Game

Join an active live game as a participant.

**Endpoint**: `POST /api/live-games/{join_code}/join`

**Authentication**: Required

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `join_code` | string | 4-character join code |

**Request Body**: None (user is identified via JWT token)

**Response** (201 Created):
```json
{
  "id": "participant-uuid",
  "live_game_id": "live-game-uuid",
  "user_id": "user-uuid",
  "display_name": "Player 1",
  "joined_at": "2025-01-15T10:35:00Z",
  "stats": {
    "chips_on_table": 0.00,
    "total_buy_ins": 0.00,
    "total_cash_outs": 0.00,
    "net_result": 0.00
  }
}
```

**Error Responses**:

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `LIVE_GAME_NOT_FOUND` | Join code does not exist |
| 400 | `GAME_CLOSED` | Cannot join a closed game |
| 400 | `ALREADY_JOINED` | User is already a participant in this live game |
| 401 | `UNAUTHORIZED` | Missing or invalid JWT token |

**Example**:
```bash
curl -X POST https://homegame.gg/api/live-games/A7X2/join \
  -H "Authorization: Bearer <token>"
```

---

### 4. Get Participants

Retrieve all participants in a live game with their current stats.

**Endpoint**: `GET /api/live-games/{join_code}/participants`

**Authentication**: Required

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `join_code` | string | 4-character join code |

**Response** (200 OK):
```json
[
  {
    "id": "participant-uuid-1",
    "live_game_id": "live-game-uuid",
    "user_id": "user-uuid-1",
    "display_name": "Player 1",
    "joined_at": "2025-01-15T10:35:00Z",
    "stats": {
      "chips_on_table": 120.00,
      "total_buy_ins": 150.00,
      "total_cash_outs": 50.00,
      "net_result": 20.00
    }
  },
  {
    "id": "participant-uuid-2",
    "live_game_id": "live-game-uuid",
    "user_id": "user-uuid-2",
    "display_name": "Player 2",
    "joined_at": "2025-01-15T10:40:00Z",
    "stats": {
      "chips_on_table": 80.00,
      "total_buy_ins": 100.00,
      "total_cash_outs": 0.00,
      "net_result": -20.00
    }
  }
]
```

**Stats Calculation**:
```
net_result = (total_cash_outs + chips_on_table) - total_buy_ins
```

**Error Responses**:

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `LIVE_GAME_NOT_FOUND` | Join code does not exist |
| 401 | `UNAUTHORIZED` | Missing or invalid JWT token |

**Example**:
```bash
curl -X GET https://homegame.gg/api/live-games/A7X2/participants \
  -H "Authorization: Bearer <token>"
```

---

### 5. Request Buy-In

Submit a buy-in transaction request (requires admin approval).

**Endpoint**: `POST /api/live-games/{join_code}/transactions/buy-in`

**Authentication**: Required (must be a participant)

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `join_code` | string | 4-character join code |

**Request Body**:
```json
{
  "amount": 50.00
}
```

**Request Schema**:
| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `amount` | number | Yes | >= min_buy_in, <= max_buy_in (if set) | Buy-in amount in dollars |

**Response** (201 Created):
```json
{
  "id": "transaction-uuid",
  "live_game_id": "live-game-uuid",
  "participant_id": "participant-uuid",
  "transaction_type": "buy_in",
  "amount": 50.00,
  "status": "pending",
  "created_at": "2025-01-15T11:00:00Z",
  "approved_at": null,
  "approved_by_user_id": null
}
```

**Error Responses**:

| Status | Error Code | Description |
|--------|------------|-------------|
| 400 | `AMOUNT_BELOW_MINIMUM` | Amount is less than min_buy_in |
| 400 | `AMOUNT_ABOVE_MAXIMUM` | Amount exceeds max_buy_in |
| 400 | `GAME_CLOSED` | Cannot create transactions in a closed game |
| 400 | `PENDING_TRANSACTION_EXISTS` | User already has a pending transaction |
| 404 | `LIVE_GAME_NOT_FOUND` | Join code does not exist |
| 404 | `PARTICIPANT_NOT_FOUND` | User is not a participant in this game |
| 401 | `UNAUTHORIZED` | Missing or invalid JWT token |

**Example**:
```bash
curl -X POST https://homegame.gg/api/live-games/A7X2/transactions/buy-in \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"amount": 50.00}'
```

---

### 6. Request Cash-Out

Submit a cash-out transaction request (requires admin approval).

**Endpoint**: `POST /api/live-games/{join_code}/transactions/cash-out`

**Authentication**: Required (must be a participant)

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `join_code` | string | 4-character join code |

**Request Body**:
```json
{
  "amount": 75.00
}
```

**Request Schema**:
| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `amount` | number | Yes | > 0, <= chips_on_table | Cash-out amount in dollars |

**Response** (201 Created):
```json
{
  "id": "transaction-uuid",
  "live_game_id": "live-game-uuid",
  "participant_id": "participant-uuid",
  "transaction_type": "cash_out",
  "amount": 75.00,
  "status": "pending",
  "created_at": "2025-01-15T11:30:00Z",
  "approved_at": null,
  "approved_by_user_id": null
}
```

**Error Responses**:

| Status | Error Code | Description |
|--------|------------|-------------|
| 400 | `INSUFFICIENT_CHIPS` | Amount exceeds chips_on_table |
| 400 | `INVALID_AMOUNT` | Amount must be greater than 0 |
| 400 | `GAME_CLOSED` | Cannot create transactions in a closed game |
| 400 | `PENDING_TRANSACTION_EXISTS` | User already has a pending transaction |
| 404 | `LIVE_GAME_NOT_FOUND` | Join code does not exist |
| 404 | `PARTICIPANT_NOT_FOUND` | User is not a participant in this game |
| 401 | `UNAUTHORIZED` | Missing or invalid JWT token |

**Example**:
```bash
curl -X POST https://homegame.gg/api/live-games/A7X2/transactions/cash-out \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"amount": 75.00}'
```

---

### 7. Get Pending Transactions

Retrieve all pending transactions for a live game (admin use).

**Endpoint**: `GET /api/live-games/{join_code}/transactions/pending`

**Authentication**: Required

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `join_code` | string | 4-character join code |

**Response** (200 OK):
```json
[
  {
    "id": "transaction-uuid-1",
    "live_game_id": "live-game-uuid",
    "participant_id": "participant-uuid-1",
    "display_name": "Player 1",
    "transaction_type": "buy_in",
    "amount": 50.00,
    "status": "pending",
    "created_at": "2025-01-15T11:00:00Z"
  },
  {
    "id": "transaction-uuid-2",
    "live_game_id": "live-game-uuid",
    "participant_id": "participant-uuid-2",
    "display_name": "Player 2",
    "transaction_type": "cash_out",
    "amount": 30.00,
    "status": "pending",
    "created_at": "2025-01-15T11:05:00Z"
  }
]
```

**Error Responses**:

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `LIVE_GAME_NOT_FOUND` | Join code does not exist |
| 401 | `UNAUTHORIZED` | Missing or invalid JWT token |

**Example**:
```bash
curl -X GET https://homegame.gg/api/live-games/A7X2/transactions/pending \
  -H "Authorization: Bearer <token>"
```

---

### 8. Approve Transaction

Approve a pending buy-in or cash-out transaction (admin only).

**Endpoint**: `POST /api/live-games/{join_code}/transactions/{transaction_id}/approve`

**Authentication**: Required (must be game creator or have admin access)

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `join_code` | string | 4-character join code |
| `transaction_id` | string (UUID) | Transaction UUID |

**Request Body**: None

**Response** (200 OK):
```json
{
  "id": "transaction-uuid",
  "live_game_id": "live-game-uuid",
  "participant_id": "participant-uuid",
  "transaction_type": "buy_in",
  "amount": 50.00,
  "status": "approved",
  "created_at": "2025-01-15T11:00:00Z",
  "approved_at": "2025-01-15T11:02:00Z",
  "approved_by_user_id": "admin-user-uuid"
}
```

**Side Effects**:
- **Buy-In**: `chips_on_table` and `total_buy_ins` increase by `amount`
- **Cash-Out**: `chips_on_table` decreases by `amount`, `total_cash_outs` increases by `amount`
- SSE event `transaction_approved` is broadcast to all participants

**Error Responses**:

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `TRANSACTION_NOT_FOUND` | transaction_id does not exist |
| 400 | `TRANSACTION_ALREADY_PROCESSED` | Transaction status is not "pending" |
| 400 | `INSUFFICIENT_CHIPS_FOR_CASHOUT` | Participant doesn't have enough chips (edge case) |
| 403 | `FORBIDDEN` | User does not have permission to approve (not game creator) |
| 401 | `UNAUTHORIZED` | Missing or invalid JWT token |

**Example**:
```bash
curl -X POST https://homegame.gg/api/live-games/A7X2/transactions/550e8400-e29b-41d4-a716-446655440000/approve \
  -H "Authorization: Bearer <token>"
```

---

### 9. Reject Transaction

Reject a pending buy-in or cash-out transaction (admin only).

**Endpoint**: `POST /api/live-games/{join_code}/transactions/{transaction_id}/reject`

**Authentication**: Required (must be game creator or have admin access)

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `join_code` | string | 4-character join code |
| `transaction_id` | string (UUID) | Transaction UUID |

**Request Body**: None

**Response** (200 OK):
```json
{
  "id": "transaction-uuid",
  "live_game_id": "live-game-uuid",
  "participant_id": "participant-uuid",
  "transaction_type": "buy_in",
  "amount": 50.00,
  "status": "rejected",
  "created_at": "2025-01-15T11:00:00Z",
  "rejected_at": "2025-01-15T11:03:00Z",
  "rejected_by_user_id": "admin-user-uuid"
}
```

**Side Effects**:
- Transaction is marked as "rejected" (no balance changes)
- SSE event `transaction_rejected` is broadcast to all participants
- Player can submit a new transaction

**Error Responses**:

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `TRANSACTION_NOT_FOUND` | transaction_id does not exist |
| 400 | `TRANSACTION_ALREADY_PROCESSED` | Transaction status is not "pending" |
| 403 | `FORBIDDEN` | User does not have permission to reject (not game creator) |
| 401 | `UNAUTHORIZED` | Missing or invalid JWT token |

**Example**:
```bash
curl -X POST https://homegame.gg/api/live-games/A7X2/transactions/550e8400-e29b-41d4-a716-446655440000/reject \
  -H "Authorization: Bearer <token>"
```

---

### 10. Get Transaction Details

Retrieve details of a specific transaction.

**Endpoint**: `GET /api/live-games/{join_code}/transactions/{transaction_id}`

**Authentication**: Required

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `join_code` | string | 4-character join code |
| `transaction_id` | string (UUID) | Transaction UUID |

**Response** (200 OK):
```json
{
  "id": "transaction-uuid",
  "live_game_id": "live-game-uuid",
  "participant_id": "participant-uuid",
  "display_name": "Player 1",
  "transaction_type": "buy_in",
  "amount": 50.00,
  "status": "approved",
  "created_at": "2025-01-15T11:00:00Z",
  "approved_at": "2025-01-15T11:02:00Z",
  "approved_by_user_id": "admin-user-uuid",
  "rejected_at": null,
  "rejected_by_user_id": null
}
```

**Error Responses**:

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `TRANSACTION_NOT_FOUND` | transaction_id does not exist |
| 401 | `UNAUTHORIZED` | Missing or invalid JWT token |

**Example**:
```bash
curl -X GET https://homegame.gg/api/live-games/A7X2/transactions/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer <token>"
```

---

### 11. Close Live Game

Close an active live game, preventing new transactions and finalizing the session.

**Endpoint**: `POST /api/live-games/{join_code}/close`

**Authentication**: Required (must be game creator)

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `join_code` | string | 4-character join code |

**Request Body**: None

**Response** (200 OK):
```json
{
  "id": "live-game-uuid",
  "game_id": "game-uuid",
  "join_code": "A7X2",
  "status": "closed",
  "min_buy_in": 20.00,
  "max_buy_in": 200.00,
  "small_blind": 0.25,
  "big_blind": 0.50,
  "created_at": "2025-01-15T10:30:00Z",
  "closed_at": "2025-01-15T14:30:00Z",
  "created_by_user_id": "user-uuid",
  "final_stats": {
    "total_buy_ins": 500.00,
    "total_cash_outs": 350.00,
    "chips_remaining": 150.00,
    "num_participants": 6
  }
}
```

**Side Effects**:
- Game status changes to "closed"
- All pending transactions are automatically rejected
- SSE event `game_closed` is broadcast to all participants
- SSE connections are terminated
- Final ledger is saved to the game's session history

**Error Responses**:

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `LIVE_GAME_NOT_FOUND` | Join code does not exist |
| 400 | `GAME_ALREADY_CLOSED` | Game is already closed |
| 403 | `FORBIDDEN` | User does not have permission to close (not game creator) |
| 401 | `UNAUTHORIZED` | Missing or invalid JWT token |

**Example**:
```bash
curl -X POST https://homegame.gg/api/live-games/A7X2/close \
  -H "Authorization: Bearer <token>"
```

---

### 12. SSE Stream (Real-Time Events)

Establish a Server-Sent Events (SSE) connection for real-time updates.

**Endpoint**: `GET /api/live-games/{join_code}/stream`

**Authentication**: Via query parameter (EventSource limitation)

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `join_code` | string | 4-character join code |

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `token` | string | Yes | JWT token for authentication |

**Response**: `text/event-stream` (continuous connection)

**Event Types**:

#### `participant_joined`
Broadcast when a new participant joins the game.

```
event: participant_joined
data: {"participant_id": "uuid", "display_name": "Player 3", "joined_at": "2025-01-15T11:00:00Z"}
```

#### `transaction_created`
Broadcast when a player submits a buy-in or cash-out request.

```
event: transaction_created
data: {"transaction_id": "uuid", "transaction_type": "buy_in", "participant_id": "uuid", "display_name": "Player 1", "amount": 50.00, "status": "pending"}
```

#### `transaction_approved`
Broadcast when admin approves a transaction.

```
event: transaction_approved
data: {"transaction_id": "uuid", "participant_id": "uuid", "display_name": "Player 1", "amount": 50.00, "approved_by_user_id": "admin-uuid", "approved_at": "2025-01-15T11:02:00Z"}
```

#### `transaction_rejected`
Broadcast when admin rejects a transaction.

```
event: transaction_rejected
data: {"transaction_id": "uuid", "participant_id": "uuid", "display_name": "Player 1", "amount": 50.00, "rejected_by_user_id": "admin-uuid", "rejected_at": "2025-01-15T11:03:00Z"}
```

#### `game_closed`
Broadcast when admin closes the game.

```
event: game_closed
data: {"closed_at": "2025-01-15T14:30:00Z", "closed_by_user_id": "admin-uuid"}
```

#### Keepalive (Comment)
Sent every 30 seconds to prevent connection timeout.

```
: keepalive
```

**Connection Limits**:
- Maximum 5 connections per user
- Maximum 100 connections per live game

**Error Responses**:

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `LIVE_GAME_NOT_FOUND` | Join code does not exist |
| 401 | `UNAUTHORIZED` | Missing or invalid JWT token |
| 429 | `TOO_MANY_CONNECTIONS` | User has exceeded connection limit |
| 503 | `GAME_CONNECTION_LIMIT_EXCEEDED` | Game has reached max connections |

**Frontend Usage (JavaScript)**:
```javascript
const token = localStorage.getItem('auth_token');
const eventSource = new EventSource(
  `/api/live-games/A7X2/stream?token=${encodeURIComponent(token)}`
);

eventSource.addEventListener('transaction_created', (event) => {
  const data = JSON.parse(event.data);
  console.log('New transaction:', data);
});

eventSource.addEventListener('transaction_approved', (event) => {
  const data = JSON.parse(event.data);
  console.log('Transaction approved:', data);
});

eventSource.onerror = (error) => {
  console.error('SSE connection error:', error);
  eventSource.close();
};

// Cleanup on unmount
eventSource.close();
```

**Auto-Reconnection Strategy**:
- Client should implement exponential backoff: 1s → 2s → 4s → 8s → 16s → 30s (max)
- Retry up to 10 times before giving up
- Invalidate React Query caches on reconnect to ensure data consistency

---

### 13. Get SSE Metrics (Admin Only)

Retrieve metrics about active SSE connections for monitoring.

**Endpoint**: `GET /api/live-games/metrics`

**Authentication**: Required (admin only)

**Response** (200 OK):
```json
{
  "total_connections": 42,
  "games": [
    {
      "live_game_id": "uuid-1",
      "join_code": "A7X2",
      "connection_count": 15,
      "participants": ["user-uuid-1", "user-uuid-2", "..."]
    },
    {
      "live_game_id": "uuid-2",
      "join_code": "B3K9",
      "connection_count": 27,
      "participants": ["user-uuid-3", "user-uuid-4", "..."]
    }
  ]
}
```

**Error Responses**:

| Status | Error Code | Description |
|--------|------------|-------------|
| 403 | `FORBIDDEN` | User does not have admin privileges |
| 401 | `UNAUTHORIZED` | Missing or invalid JWT token |

**Example**:
```bash
curl -X GET https://homegame.gg/api/live-games/metrics \
  -H "Authorization: Bearer <token>"
```

---

## Error Handling

### Standard Error Response Format

All API errors return a consistent JSON structure:

```json
{
  "error": {
    "code": "ERROR_CODE_CONSTANT",
    "message": "Human-readable error description",
    "details": {
      "field": "Additional context (optional)"
    }
  }
}
```

### HTTP Status Codes

| Status Code | Meaning | Common Scenarios |
|-------------|---------|------------------|
| 200 OK | Request succeeded | GET requests, successful approvals/rejections |
| 201 Created | Resource created | POST create live game, join, buy-in/cash-out |
| 400 Bad Request | Invalid input | Validation errors, business rule violations |
| 401 Unauthorized | Missing/invalid auth | No JWT token, expired token |
| 403 Forbidden | Insufficient permissions | Non-admin trying to approve transactions |
| 404 Not Found | Resource doesn't exist | Invalid join code, transaction ID |
| 429 Too Many Requests | Rate limit exceeded | Too many SSE connections |
| 500 Internal Server Error | Server error | Database failure, unexpected exception |
| 503 Service Unavailable | Service overloaded | SSE connection limit reached |

### Common Error Codes

| Code | HTTP Status | Description | Resolution |
|------|-------------|-------------|------------|
| `UNAUTHORIZED` | 401 | JWT token missing or invalid | Re-authenticate via /api/auth/login |
| `FORBIDDEN` | 403 | User lacks permission | Ensure user has admin access |
| `LIVE_GAME_NOT_FOUND` | 404 | Join code doesn't exist | Verify join code with admin |
| `GAME_ALREADY_CLOSED` | 400 | Cannot modify closed game | Create a new live game |
| `PENDING_TRANSACTION_EXISTS` | 400 | User already has pending transaction | Wait for admin approval/rejection |
| `INSUFFICIENT_CHIPS` | 400 | Cash-out exceeds chips on table | Reduce cash-out amount |
| `AMOUNT_BELOW_MINIMUM` | 400 | Buy-in below min_buy_in | Increase buy-in amount |
| `AMOUNT_ABOVE_MAXIMUM` | 400 | Buy-in exceeds max_buy_in | Reduce buy-in amount |
| `TOO_MANY_CONNECTIONS` | 429 | User exceeded SSE connection limit (5) | Close other browser tabs |
| `GAME_CONNECTION_LIMIT_EXCEEDED` | 503 | Game exceeded SSE connection limit (100) | Wait for others to disconnect |
| `TRANSACTION_ALREADY_PROCESSED` | 400 | Transaction is not in "pending" status | Transaction was already approved/rejected |

---

## Rate Limiting

**Global Limits** (via Flask-Limiter):
- 2000 requests per day
- 500 requests per hour

**SSE Connection Limits**:
- 5 concurrent connections per user
- 100 concurrent connections per live game

**Rate Limit Headers**:
```http
X-RateLimit-Limit: 500
X-RateLimit-Remaining: 487
X-RateLimit-Reset: 1610723400
```

**Rate Limit Exceeded Response** (429 Too Many Requests):
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again in 3600 seconds.",
    "details": {
      "retry_after": 3600
    }
  }
}
```

---

## Webhooks (Future Feature)

Webhook support for external integrations is planned for a future release. This would allow third-party apps to receive Live Game events without maintaining SSE connections.

**Planned Endpoint**: `POST /api/live-games/{join_code}/webhooks`

**Planned Events**:
- `live_game.created`
- `live_game.closed`
- `transaction.created`
- `transaction.approved`
- `transaction.rejected`

---

## API Versioning

**Current Version**: v1 (implicit in all URLs)

**Future Versioning Strategy**:
- Breaking changes will introduce `/api/v2/*` endpoints
- v1 endpoints will be maintained for 12 months after v2 release
- Deprecation warnings will be sent via `X-API-Deprecation` header

---

## Best Practices

### Client Implementation Guidelines

1. **Always Handle Errors Gracefully**
   ```javascript
   try {
     const response = await fetch('/api/live-games/A7X2/participants', {
       headers: { 'Authorization': `Bearer ${token}` }
     });

     if (!response.ok) {
       const error = await response.json();
       // Handle error.code specifically
       if (error.code === 'LIVE_GAME_NOT_FOUND') {
         // Redirect to join page
       }
     }
   } catch (err) {
     // Handle network errors
   }
   ```

2. **Use SSE for Real-Time Updates (Not Polling)**
   - SSE reduces HTTP requests by 99%+
   - Implement auto-reconnection with exponential backoff
   - Invalidate React Query caches on SSE events

3. **Validate Input Client-Side**
   - Check buy-in amount against min/max before submitting
   - Verify chips_on_table before allowing cash-out
   - Disable buttons during pending transactions

4. **Retry Transient Errors**
   - 500/503 errors: Retry with exponential backoff
   - 429 errors: Respect `retry_after` header
   - 401 errors: Refresh JWT token and retry once

5. **Cache JWT Tokens Securely**
   - Store in `localStorage` (web) or secure storage (mobile)
   - Never include tokens in URLs (except SSE, unavoidable)
   - Implement token refresh logic before expiration

---

## Testing

### Development Environment

**Base URL**: `http://localhost:8000/api`

**Test Account**:
```json
{
  "email": "test@example.com",
  "password": "testpassword123"
}
```

### Example: Full Workflow Test

```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpassword123"}' \
  | jq -r '.token')

# 2. Create Live Game
LIVE_GAME=$(curl -s -X POST http://localhost:8000/api/live-games \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "game_id": "550e8400-e29b-41d4-a716-446655440000",
    "min_buy_in": 20.00,
    "max_buy_in": 200.00
  }')

JOIN_CODE=$(echo $LIVE_GAME | jq -r '.join_code')
echo "Join Code: $JOIN_CODE"

# 3. Join as Participant
curl -X POST http://localhost:8000/api/live-games/$JOIN_CODE/join \
  -H "Authorization: Bearer $TOKEN"

# 4. Request Buy-In
TRANSACTION=$(curl -s -X POST http://localhost:8000/api/live-games/$JOIN_CODE/transactions/buy-in \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 50.00}')

TRANSACTION_ID=$(echo $TRANSACTION | jq -r '.id')

# 5. Approve Transaction (as admin)
curl -X POST http://localhost:8000/api/live-games/$JOIN_CODE/transactions/$TRANSACTION_ID/approve \
  -H "Authorization: Bearer $TOKEN"

# 6. Get Participants (verify balance updated)
curl -X GET http://localhost:8000/api/live-games/$JOIN_CODE/participants \
  -H "Authorization: Bearer $TOKEN" | jq

# 7. Close Game
curl -X POST http://localhost:8000/api/live-games/$JOIN_CODE/close \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## Production Deployment

### Environment Variables

Required for production:

```bash
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=<strong-secret-key>

# Database
DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname

# JWT Configuration
JWT_SECRET=<strong-jwt-secret>
JWT_EXPIRATION_DAYS=7

# CORS
ALLOWED_ORIGINS=https://homegame.gg,https://www.homegame.gg

# Rate Limiting
RATELIMIT_STORAGE_URL=redis://redis:6379/0

# SSE (Optional - for Redis Pub/Sub)
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=<redis-password>
USE_REDIS_PUBSUB=true  # Enable for multi-instance deployments
```

### Health Checks

**Endpoint**: `GET /api/health`

**Response** (200 OK):
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

Use this endpoint for Kubernetes/Docker health checks and load balancer monitoring.

---

## Migration to Redis Pub/Sub (Multi-Instance)

For production deployments with multiple server instances behind a load balancer, migrate from in-memory SSE to Redis Pub/Sub.

**See**: `docs/SSE_REDIS_UPGRADE.md` for detailed migration guide.

**Key Changes**:
1. Set `USE_REDIS_PUBSUB=true`
2. Configure Redis connection (REDIS_HOST, REDIS_PORT, REDIS_PASSWORD)
3. Deploy multiple instances
4. Test SSE across instances

**Cost**: ~$30-90/month for GCP Memorystore (Basic tier)

---

## Support and Feedback

- **Documentation**: See `docs/LIVE_GAME_USER_GUIDE.md` for user-facing documentation
- **Bug Reports**: https://github.com/edunbar/mmpt-clean/issues
- **API Changes**: Subscribe to release notes for deprecation warnings

---

**Last Updated**: 2025-01-XX
**Version**: 1.0.0
**Status**: Production Ready ✅
