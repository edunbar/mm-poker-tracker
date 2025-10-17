"""
Authentication middleware for Flask routes.

This module provides decorators for protecting routes that require
authenticated users via Clerk tokens or admin codes.
"""

import os
from functools import wraps
from flask import request, jsonify, g
from datetime import datetime, timezone, timedelta

from db.models import Game, User
from db.database import SessionLocal


def require_auth_or_admin_code(f):
    """
    Validates Clerk token OR admin code from headers.
    Does NOT check game ownership or admin code expiration.

    Sets:
        - g.auth_method: 'clerk' or 'admin_code'
        - g.current_user_id (if Clerk)
        - g.current_user_email (if Clerk)
        - g.admin_code (if admin code)

    Returns 401 only for authentication failures.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Try Clerk authentication first
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1] if len(auth_header.split(' ')) > 1 else None

            if token:
                try:
                    from clerk_backend_api import Clerk
                    from clerk_backend_api.jwks_helpers import AuthenticateRequestOptions

                    clerk_secret = os.environ.get('CLERK_SECRET_KEY')
                    if clerk_secret:
                        clerk_client = Clerk(bearer_auth=clerk_secret)
                        request_state = clerk_client.verify_token(token, options=AuthenticateRequestOptions())

                        clerk_user_id = request_state.get('sub')
                        if clerk_user_id:
                            # Look up user by clerk_user_id
                            db = SessionLocal()
                            try:
                                user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
                                if user:
                                    g.auth_method = 'clerk'
                                    g.current_user_id = str(user.id)
                                    g.current_user_email = user.email
                                    return f(*args, **kwargs)
                            finally:
                                db.close()
                except Exception:
                    # Clerk validation failed, try admin code fallback
                    pass

        # Fallback to admin code
        admin_code = request.headers.get('X-Admin-Code')
        if admin_code:
            g.auth_method = 'admin_code'
            g.admin_code = admin_code
            return f(*args, **kwargs)

        # No valid auth provided
        return jsonify({'error': 'Missing authentication: provide Clerk token or X-Admin-Code'}), 401

    return decorated_function


def check_game_authorization(game: Game, auth_method: str,
                            user_id: str = None, admin_code: str = None) -> tuple:
    """
    Check if user/admin is authorized for this game.

    Args:
        game: Game object
        auth_method: 'clerk' or 'admin_code'
        user_id: User UUID (for Clerk auth)
        admin_code: Admin code string (for admin code auth)

    Returns:
        (authorized: bool, error_message: str)
    """
    if auth_method == 'clerk':
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
