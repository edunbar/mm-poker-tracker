"""
Live Game Server-Sent Events (SSE) for real-time updates.

This module provides SSE endpoints for broadcasting live game events to connected
clients, enabling instant UI updates without polling.

Features:
- Real-time event broadcasting (transactions, participants, game closure)
- Connection limits (5 per user, 100 per game) to prevent resource exhaustion
- Thread-safe connection management
- Automatic keepalive heartbeat (30s)
- Metrics endpoint for monitoring
- Graceful cleanup on client disconnect

Production Notes:
- In-memory connection storage: Single-instance deployment only
- For multi-instance: Migrate to Redis Pub/Sub (see docs/SSE_REDIS_UPGRADE.md)
- JWT tokens in query params may appear in logs (security consideration)
"""

import json
import time
import queue
from threading import Lock
from typing import Dict, Set
from datetime import datetime

from flask import Blueprint, Response, request, jsonify, g, stream_with_context

from db.database import SessionLocal
from middleware.auth_middleware import require_auth, get_jwt_service
from infrastructure.persistence.sqlalchemy import SQLAlchemyLiveGameRepository
from domain.live_game.value_objects import JoinCode

# Create blueprint
live_game_sse_bp = Blueprint('live_game_sse', __name__)

# ============================================================================
# Connection Registry (Thread-Safe)
# ============================================================================

# In-memory connection storage
# Format: {live_game_id: {user_id: queue.Queue}}
_connections: Dict[str, Dict[str, queue.Queue]] = {}
_connections_lock = Lock()

# Metrics
_metrics = {
    'total_connections': 0,
    'total_events_sent': 0,
    'connections_refused_user_limit': 0,
    'connections_refused_game_limit': 0,
    'started_at': datetime.utcnow().isoformat()
}
_metrics_lock = Lock()

# Connection limits
MAX_CONNECTIONS_PER_USER = 5  # Prevent single user from hogging resources
MAX_CONNECTIONS_PER_GAME = 100  # Reasonable limit for live poker games


# ============================================================================
# Helper Functions
# ============================================================================

def resolve_live_game_id(join_code: str) -> str | None:
    """
    Resolve live game ID from join code.

    Args:
        join_code: 4-character join code (e.g., "A3B7")

    Returns:
        Live game ID (UUID string) or None if not found
    """
    session = SessionLocal()
    try:
        live_game_repo = SQLAlchemyLiveGameRepository(session)
        live_game = live_game_repo.get_by_join_code(JoinCode(join_code.strip().upper()))

        if not live_game:
            return None

        return str(live_game.id)
    finally:
        session.close()


def count_user_connections(user_id: str) -> int:
    """
    Count total connections across all games for a user.

    Args:
        user_id: User UUID string

    Returns:
        Total number of active connections for this user
    """
    with _connections_lock:
        count = 0
        for game_connections in _connections.values():
            if user_id in game_connections:
                count += 1
        return count


def count_game_connections(live_game_id: str) -> int:
    """
    Count total connections for a specific game.

    Args:
        live_game_id: Live game UUID string

    Returns:
        Number of active connections for this game
    """
    with _connections_lock:
        return len(_connections.get(live_game_id, {}))


def add_connection(live_game_id: str, user_id: str) -> tuple[queue.Queue | None, str | None]:
    """
    Add SSE connection to the registry with limit enforcement.

    Args:
        live_game_id: Live game UUID string
        user_id: User UUID string

    Returns:
        (queue, error_message) - Queue for sending events, or (None, error) if limit exceeded
    """
    with _connections_lock:
        # Check user connection limit
        user_conn_count = 0
        for game_connections in _connections.values():
            if user_id in game_connections:
                user_conn_count += 1

        if user_conn_count >= MAX_CONNECTIONS_PER_USER:
            with _metrics_lock:
                _metrics['connections_refused_user_limit'] += 1
            return None, f"Connection limit exceeded: You have {user_conn_count} active connections (max: {MAX_CONNECTIONS_PER_USER})"

        # Check game connection limit
        if live_game_id not in _connections:
            _connections[live_game_id] = {}

        game_conn_count = len(_connections[live_game_id])
        if game_conn_count >= MAX_CONNECTIONS_PER_GAME:
            with _metrics_lock:
                _metrics['connections_refused_game_limit'] += 1
            return None, f"Game connection limit exceeded: {game_conn_count} active connections (max: {MAX_CONNECTIONS_PER_GAME})"

        # Create queue and add connection
        q = queue.Queue(maxsize=10)
        _connections[live_game_id][user_id] = q

        with _metrics_lock:
            _metrics['total_connections'] += 1

        return q, None


def remove_connection(live_game_id: str, user_id: str):
    """
    Remove SSE connection from the registry.

    Args:
        live_game_id: Live game UUID string
        user_id: User UUID string
    """
    with _connections_lock:
        if live_game_id in _connections:
            _connections[live_game_id].pop(user_id, None)

            # Clean up empty game entries
            if not _connections[live_game_id]:
                del _connections[live_game_id]


def broadcast_event(live_game_id: str, event_type: str, data: dict):
    """
    Broadcast event to all connections for a live game.

    Args:
        live_game_id: Live game UUID string
        event_type: Event name (e.g., "transaction_created")
        data: Event payload as dict (will be JSON-serialized)

    Event Format:
        event: transaction_created
        data: {"transaction_id": "...", "amount": 50.00}

    """
    with _connections_lock:
        if live_game_id not in _connections:
            return  # No active connections for this game

        # Format SSE message
        message = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

        # Send to all connected clients
        sent_count = 0
        for user_id, q in list(_connections[live_game_id].items()):
            try:
                q.put_nowait(message)
                sent_count += 1
            except queue.Full:
                # Skip if queue is full (client not consuming fast enough)
                pass

        with _metrics_lock:
            _metrics['total_events_sent'] += sent_count


# ============================================================================
# SSE Endpoints
# ============================================================================

@live_game_sse_bp.route('/live-games/<join_code>/stream', methods=['GET'])
def stream_live_game_events(join_code):
    """
    Server-Sent Events stream for live game updates.

    Query Parameters:
        token: JWT authentication token (required)

    Path Parameters:
        join_code: 4-character join code (e.g., "A3B7")

    Returns:
        200: SSE stream with events
        401: Unauthorized (invalid/missing token)
        404: Live game not found
        429: Too many connections (user or game limit exceeded)

    Event Types:
        - participant_joined: New player joined the game
        - transaction_created: Buy-in/cash-out request created
        - transaction_approved: Transaction approved by admin
        - transaction_rejected: Transaction rejected by admin
        - transaction_edited: Transaction amount modified
        - game_closed: Game has been closed

    Security Note:
        JWT token passed via query param (EventSource limitation).
        Tokens may appear in server logs. Consider short-lived SSE tokens in production.
    """
    # Manual JWT validation (EventSource can't send Authorization header)
    token = request.args.get('token')

    if not token:
        return Response("Missing token query parameter", status=401)

    # Validate JWT token
    try:
        jwt_service = get_jwt_service()
        payload = jwt_service.decode_token(token)

        if not payload:
            return Response("Invalid or expired token", status=401)

        user_id = payload.get('user_id')
        if not user_id:
            return Response("Token missing user_id", status=401)

    except Exception as e:
        return Response(f"Token validation error: {str(e)}", status=401)

    # Resolve live game ID from join code
    live_game_id = resolve_live_game_id(join_code)

    if not live_game_id:
        return Response(f"Live game not found for code: {join_code}", status=404)

    # Create queue for this connection (with limits)
    message_queue, error = add_connection(live_game_id, user_id)

    if error:
        return Response(error, status=429)

    def generate():
        """
        SSE event generator with keepalive.
        """
        try:
            # Send initial connection confirmation
            yield f"data: {json.dumps({'type': 'connected', 'join_code': join_code})}\n\n"

            # Stream events
            while True:
                try:
                    # Wait for message with timeout (allows keepalive)
                    message = message_queue.get(timeout=30)
                    yield message

                except queue.Empty:
                    # Send keepalive comment every 30 seconds
                    # (prevents connection timeout, not visible to EventSource)
                    yield ": keepalive\n\n"

        except GeneratorExit:
            # Client disconnected gracefully
            remove_connection(live_game_id, user_id)
        except Exception as e:
            # Error occurred, cleanup connection
            remove_connection(live_game_id, user_id)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',  # Disable nginx buffering
            'Connection': 'keep-alive',
        }
    )


@live_game_sse_bp.route('/live-games/sse/metrics', methods=['GET'])
@require_auth
def get_sse_metrics():
    """
    Get SSE connection metrics for monitoring.

    Requires authentication (admin monitoring).

    Returns:
        200: {
            "total_connections": 42,
            "total_events_sent": 1337,
            "connections_refused_user_limit": 3,
            "connections_refused_game_limit": 1,
            "started_at": "2025-10-10T12:00:00",
            "active_games": {
                "game_uuid_1": 15,
                "game_uuid_2": 8
            },
            "user_connections": {
                "user_uuid_1": 2,
                "user_uuid_2": 1
            }
        }
    """
    with _connections_lock:
        # Count connections per game
        active_games = {
            game_id: len(connections)
            for game_id, connections in _connections.items()
        }

        # Count connections per user
        user_connections: Dict[str, int] = {}
        for game_connections in _connections.values():
            for user_id in game_connections.keys():
                user_connections[user_id] = user_connections.get(user_id, 0) + 1

    with _metrics_lock:
        metrics_snapshot = _metrics.copy()

    return jsonify({
        **metrics_snapshot,
        'active_games': active_games,
        'user_connections': user_connections,
        'current_active_connections': sum(active_games.values())
    }), 200
