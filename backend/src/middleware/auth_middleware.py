"""
Authentication middleware for Flask routes.

This module provides decorators for protecting routes that require
authenticated users via JWT tokens or admin codes.
"""

import os
from functools import wraps
from flask import request, jsonify, g
from datetime import datetime, timezone, timedelta

from infrastructure.security import JWTTokenService
from db.models import Game


# JWT service singleton for efficiency
_jwt_service = None

def get_jwt_service():
    """Lazy-load JWT service singleton"""
    global _jwt_service
    if _jwt_service is None:
        secret = os.environ.get('JWT_SECRET')
        if not secret:
            raise RuntimeError("JWT_SECRET environment variable not set")
        _jwt_service = JWTTokenService(secret)
    return _jwt_service


def require_auth(f):
    """
    Decorator to require JWT authentication for a route.

    This decorator:
    1. Extracts JWT from Authorization: Bearer <token> header
    2. Validates token using JWTTokenService
    3. Injects user info into Flask's g object:
       - g.current_user_id (str): User's UUID
       - g.current_user_email (str): User's email
    4. Returns 401 JSON response if authentication fails

    Usage:
        >>> @app.route('/protected')
        >>> @require_auth
        >>> def protected_route():
        >>>     user_id = g.current_user_id
        >>>     return jsonify({'user_id': user_id})

    Returns:
        401 JSON response if:
        - Authorization header is missing
        - Token format is invalid (not "Bearer <token>")
        - Token is expired or invalid
        - JWT_SECRET environment variable is not set

    Note:
        The decorated function can access:
        - g.current_user_id (str)
        - g.current_user_email (str)
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get Authorization header
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({
                'error': 'Missing authorization header'
            }), 401

        # Check format: "Bearer <token>"
        if not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Invalid authorization header format. Expected: Bearer <token>'
            }), 401

        # Extract token
        token = auth_header.split(' ')[1] if len(auth_header.split(' ')) > 1 else None

        if not token:
            return jsonify({
                'error': 'Missing token in authorization header'
            }), 401

        # Get JWT service (reads JWT_SECRET from environment)
        try:
            jwt_service = get_jwt_service()
        except RuntimeError as e:
            return jsonify({
                'error': str(e)
            }), 500
        except Exception as e:
            return jsonify({
                'error': f'Authentication service error: {str(e)}'
            }), 500

        # Decode and validate token
        payload = jwt_service.decode_token(token)

        if not payload:
            return jsonify({
                'error': 'Invalid or expired token'
            }), 401

        # Inject user info into Flask's g object
        g.current_user_id = payload.get('user_id')
        g.current_user_email = payload.get('email')

        # Call the decorated function
        return f(*args, **kwargs)

    return decorated_function


def require_auth_or_admin_code(f):
    """
    Validates JWT OR admin code from headers.
    Does NOT check game ownership or admin code expiration.

    Sets:
        - g.auth_method: 'jwt' or 'admin_code'
        - g.current_user_id (if JWT)
        - g.current_user_email (if JWT)
        - g.admin_code (if admin code)

    Returns 401 only for authentication failures.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Try JWT first
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1] if len(auth_header.split(' ')) > 1 else None

            if token:
                try:
                    jwt_service = get_jwt_service()
                    payload = jwt_service.decode_token(token)

                    if payload:
                        g.auth_method = 'jwt'
                        g.current_user_id = payload.get('user_id')
                        g.current_user_email = payload.get('email')
                        return f(*args, **kwargs)
                except Exception:
                    # JWT validation failed, try admin code fallback
                    pass

        # Fallback to admin code
        admin_code = request.headers.get('X-Admin-Code')
        if admin_code:
            g.auth_method = 'admin_code'
            g.admin_code = admin_code
            return f(*args, **kwargs)

        # No valid auth provided
        return jsonify({'error': 'Missing authentication: provide JWT token or X-Admin-Code'}), 401

    return decorated_function


def check_game_authorization(game: Game, auth_method: str,
                            user_id: str = None, admin_code: str = None) -> tuple:
    """
    Check if user/admin is authorized for this game.

    Args:
        game: Game object
        auth_method: 'jwt' or 'admin_code'
        user_id: User UUID (for JWT auth)
        admin_code: Admin code string (for admin code auth)

    Returns:
        (authorized: bool, error_message: str)
    """
    if auth_method == 'jwt':
        # JWT auth: must be game owner
        if game.owner_user_id is None:
            return False, "Game not claimed. Use admin code or claim this game first."
        if str(game.owner_user_id) != str(user_id):
            return False, "Not authorized: you do not own this game"
        return True, ""

    elif auth_method == 'admin_code':
        # Verify admin code matches
        if game.admin_code != admin_code:
            return False, "Invalid admin code"

        # Check expiration logic
        if game.owner_user_id is None:
            # Not claimed - admin code always works
            return True, ""
        elif game.admin_code_expires_at and datetime.now(timezone.utc) < game.admin_code_expires_at:
            # Claimed but within grace period
            return True, ""
        else:
            # Claimed and expired
            return False, "Admin code expired. Please claim this game with your account."

    return False, "Unknown auth method"
