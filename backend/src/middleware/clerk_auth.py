"""
Clerk authentication middleware for Flask routes.

This module provides decorators for protecting routes that require
authenticated users via Clerk session tokens.
"""

import os
from functools import wraps
from flask import request, jsonify, g
from clerk_backend_api import Clerk
import jwt
from jwt import PyJWKClient

from db.database import SessionLocal
from db.models import User
from infrastructure.persistence.sqlalchemy.user_repository import SQLAlchemyUserRepository


# Clerk client singleton for efficiency (used for user management API calls)
_clerk_client = None

# PyJWKClient for JWT verification (cached for performance)
_jwks_client = None


def get_clerk_client():
    """Lazy-load Clerk client singleton for user management API"""
    global _clerk_client
    if _clerk_client is None:
        secret_key = os.environ.get('CLERK_SECRET_KEY')
        if not secret_key:
            raise RuntimeError("CLERK_SECRET_KEY environment variable not set")
        _clerk_client = Clerk(bearer_auth=secret_key)
    return _clerk_client


def get_jwks_client():
    """Lazy-load PyJWKClient singleton for JWT verification"""
    global _jwks_client
    if _jwks_client is None:
        jwks_url = os.environ.get('CLERK_JWKS_URL')
        if not jwks_url:
            raise RuntimeError("CLERK_JWKS_URL environment variable not set")
        _jwks_client = PyJWKClient(
            jwks_url,
            cache_jwk_set=True,
            lifespan=360  # Cache JWKS for 6 minutes
        )
    return _jwks_client


def clerk_required(f):
    """
    Decorator to require Clerk authentication for a route.

    This decorator:
    1. Extracts session token from Authorization: Bearer <token> header
    2. Validates token using PyJWT with Clerk's JWKS (RS256 signature)
    3. Gets or creates User record by clerk_user_id
    4. Injects user into Flask's g object:
       - g.current_user (User): Full User model object
    5. Returns 401 JSON response if authentication fails

    Usage:
        >>> @app.route('/protected')
        >>> @clerk_required
        >>> def protected_route():
        >>>     user = get_current_user()
        >>>     return jsonify({'user_id': str(user.id)})

    Returns:
        401 JSON response if:
        - Authorization header is missing
        - Token format is invalid (not "Bearer <token>")
        - Token is expired or invalid
        - CLERK_JWKS_URL environment variable is not set

    Note:
        The decorated function can access:
        - g.current_user (User model object)
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

        # Verify JWT token using PyJWT + JWKS
        try:
            # Get JWKS client
            jwks_client = get_jwks_client()

            # Get signing key from JWKS
            signing_key = jwks_client.get_signing_key_from_jwt(token)

            # Decode and verify JWT
            decoded = jwt.decode(
                token,
                signing_key.key,
                algorithms=['RS256'],
                options={
                    'verify_signature': True,
                    'verify_exp': True,
                    'verify_nbf': True,
                    'verify_iat': True,
                    'verify_aud': False,  # Clerk doesn't always include aud
                    'verify_iss': False,  # We trust JWKS source
                }
            )

            # Extract clerk_user_id from the verified token
            clerk_user_id = decoded.get('sub')

            if not clerk_user_id:
                return jsonify({
                    'error': 'Invalid token: missing user ID (sub claim)'
                }), 401

        except jwt.ExpiredSignatureError:
            return jsonify({
                'error': 'Token has expired'
            }), 401
        except jwt.InvalidTokenError as e:
            return jsonify({
                'error': f'Invalid token: {str(e)}'
            }), 401
        except RuntimeError as e:
            return jsonify({
                'error': str(e)
            }), 500
        except Exception as e:
            return jsonify({
                'error': f'Authentication service error: {str(e)}'
            }), 500

        # Get or create user in database
        db = SessionLocal()
        try:
            user_repo = SQLAlchemyUserRepository(db)

            # Try to find user by clerk_user_id
            user = user_repo.find_by_clerk_id(clerk_user_id)

            if not user:
                # Fetch user details from Clerk to create new user
                try:
                    # Get Clerk client for user management API
                    clerk_client = get_clerk_client()
                    clerk_user = clerk_client.users.get(user_id=clerk_user_id)

                    # Create new user with Clerk data
                    # Extract email (Clerk uses email_addresses array)
                    email = None
                    if clerk_user.email_addresses:
                        primary_email = next(
                            (e for e in clerk_user.email_addresses if e.id == clerk_user.primary_email_address_id),
                            clerk_user.email_addresses[0]
                        )
                        email = primary_email.email_address

                    if not email:
                        return jsonify({
                            'error': 'User has no email address'
                        }), 400

                    # Get display name (prefer first_name + last_name, fallback to username or email)
                    display_name = None
                    if clerk_user.first_name and clerk_user.last_name:
                        display_name = f"{clerk_user.first_name} {clerk_user.last_name}"
                    elif clerk_user.first_name:
                        display_name = clerk_user.first_name
                    elif clerk_user.username:
                        display_name = clerk_user.username
                    else:
                        display_name = email.split('@')[0]

                    # Create user
                    from domain.identity import Email as EmailVO
                    email_vo = EmailVO(email)

                    user = user_repo.create_from_clerk(
                        clerk_user_id=clerk_user_id,
                        email=email_vo,
                        display_name=display_name,
                        email_verified=clerk_user.email_addresses[0].verification.status == 'verified' if clerk_user.email_addresses else False
                    )

                    db.commit()

                except Exception as create_error:
                    db.rollback()
                    return jsonify({
                        'error': f'Failed to create user: {str(create_error)}'
                    }), 500

            # Inject user into Flask's g object
            g.current_user = user

        finally:
            db.close()

        # Call the decorated function
        return f(*args, **kwargs)

    return decorated_function


def get_current_user():
    """
    Get the current authenticated user from Flask's g context.

    This helper function retrieves the User object that was injected
    by the @clerk_required decorator.

    Returns:
        User: The authenticated User model object

    Raises:
        AttributeError: If called outside of a @clerk_required route

    Usage:
        >>> @app.route('/profile')
        >>> @clerk_required
        >>> def get_profile():
        >>>     user = get_current_user()
        >>>     return jsonify({'email': user.email})
    """
    if not hasattr(g, 'current_user'):
        raise AttributeError(
            "get_current_user() can only be called within a @clerk_required route. "
            "Make sure your route is decorated with @clerk_required"
        )

    return g.current_user
