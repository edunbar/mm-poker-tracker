"""
Authentication API routes.

This module provides endpoints for user registration, login, and
retrieving current user information.
"""

import os
from flask import Blueprint, request, jsonify, g

from extensions import limiter
from db.database import SessionLocal
from domain.identity import Email, AuthenticationService
from infrastructure.security import BcryptPasswordHasher, JWTTokenService
from infrastructure.persistence.sqlalchemy.user_repository import SQLAlchemyUserRepository
from middleware.auth_middleware import require_auth

# Create blueprint
auth_bp = Blueprint('auth', __name__)


# ============================================================================
# Helper Functions (Dependency Injection)
# ============================================================================

def get_auth_service(db_session) -> AuthenticationService:
    """
    Create AuthenticationService with all dependencies.

    This helper prevents code duplication across routes and centralizes
    dependency injection.

    Args:
        db_session: SQLAlchemy database session

    Returns:
        Configured AuthenticationService instance
    """
    user_repo = SQLAlchemyUserRepository(db_session)
    password_hasher = BcryptPasswordHasher()
    return AuthenticationService(password_hasher, user_repo)


def get_token_service() -> JWTTokenService:
    """
    Get JWT token service with secret from environment.

    Reads JWT_SECRET from environment and creates JWTTokenService.

    Returns:
        Configured JWTTokenService instance

    Raises:
        RuntimeError: If JWT_SECRET environment variable is not set
    """
    jwt_secret = os.environ.get('JWT_SECRET')
    if not jwt_secret:
        raise RuntimeError(
            "JWT_SECRET environment variable not configured. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
        )
    return JWTTokenService(secret_key=jwt_secret)


# ============================================================================
# API Routes
# ============================================================================

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user account.

    Request Body:
        {
            "email": "user@example.com",
            "password": "SecurePassword123!",
            "display_name": "John Doe"
        }

    Returns:
        201: {
            "user": {
                "id": "uuid",
                "email": "user@example.com",
                "display_name": "John Doe"
            },
            "access_token": "jwt_token_string"
        }

        400: { "error": "validation or business logic error message" }
        500: { "error": "server error message" }

    Note:
        Password requirements enforced by AuthenticationService:
        - Minimum 12 characters
        - Maximum 72 characters (bcrypt limit)
    """
    db = SessionLocal()
    try:
        # Parse request
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        # Validate required fields
        if 'email' not in data:
            return jsonify({'error': 'Missing required field: email'}), 400
        if 'password' not in data:
            return jsonify({'error': 'Missing required field: password'}), 400
        if 'display_name' not in data:
            return jsonify({'error': 'Missing required field: display_name'}), 400

        # Validate and create Email value object
        try:
            email = Email(data['email'])
        except ValueError as e:
            return jsonify({'error': f'Invalid email: {str(e)}'}), 400

        password = data['password']
        display_name = data['display_name']

        # Create authentication service
        auth_service = get_auth_service(db)

        # Register user (returns Result[User])
        result = auth_service.register(email, password, display_name)

        # Handle failure
        if result.is_failure():
            return jsonify({'error': result.error}), 400

        # Success - get user and generate JWT
        user = result.value  # SQLAlchemy User model

        token_service = get_token_service()
        access_token = token_service.generate_access_token(
            str(user.id),
            user.email
        )

        return jsonify({
            'user': {
                'id': str(user.id),
                'email': user.email,
                'display_name': user.display_name
            },
            'access_token': access_token
        }), 201

    except RuntimeError as e:
        # JWT_SECRET not configured
        return jsonify({'error': str(e)}), 500

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

    finally:
        db.close()


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    """
    Authenticate user and generate access token.

    Request Body:
        {
            "email": "user@example.com",
            "password": "SecurePassword123!"
        }

    Returns:
        200: {
            "user": {
                "id": "uuid",
                "email": "user@example.com",
                "display_name": "John Doe",
                "email_verified": false,
                "last_login_at": "2025-01-15T10:30:00Z"
            },
            "access_token": "jwt_token_string"
        }

        401: { "error": "Invalid credentials" }
        400: { "error": "validation error message" }
        500: { "error": "server error message" }

    Security Notes:
        - Rate limited to 5 attempts per minute per IP
        - Returns generic "Invalid credentials" for both non-existent users
          and incorrect passwords to prevent email enumeration
        - Updates last_login_at timestamp on successful login
    """
    db = SessionLocal()
    try:
        # Parse request
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        # Validate required fields
        if 'email' not in data:
            return jsonify({'error': 'Missing required field: email'}), 400
        if 'password' not in data:
            return jsonify({'error': 'Missing required field: password'}), 400

        # Validate and create Email value object
        try:
            email = Email(data['email'])
        except ValueError as e:
            return jsonify({'error': f'Invalid email: {str(e)}'}), 400

        password = data['password']

        # Create authentication service
        auth_service = get_auth_service(db)

        # Authenticate user (returns Result[User])
        result = auth_service.login(email, password)

        # Handle failure (generic error for security)
        if result.is_failure():
            return jsonify({'error': 'Invalid credentials'}), 401

        # Success - get user and generate JWT
        user = result.value  # SQLAlchemy User model

        token_service = get_token_service()
        access_token = token_service.generate_access_token(
            str(user.id),
            user.email
        )

        return jsonify({
            'user': {
                'id': str(user.id),
                'email': user.email,
                'display_name': user.display_name,
                'email_verified': user.email_verified,
                'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None
            },
            'access_token': access_token
        }), 200

    except RuntimeError as e:
        # JWT_SECRET not configured
        return jsonify({'error': str(e)}), 500

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Login failed: {str(e)}'}), 500

    finally:
        db.close()


@auth_bp.route('/me', methods=['GET'])
@require_auth
def get_current_user():
    """
    Get current authenticated user information.

    Headers:
        Authorization: Bearer <jwt_token>

    Returns:
        200: {
            "id": "uuid",
            "email": "user@example.com",
            "display_name": "John Doe",
            "email_verified": false,
            "created_at": "2025-01-01T00:00:00Z",
            "last_login_at": "2025-01-15T10:30:00Z"
        }

        401: { "error": "authentication error message" }
        404: { "error": "User not found" }
        500: { "error": "server error message" }

    Note:
        Requires valid JWT token in Authorization header.
        User info is injected by @require_auth decorator:
        - g.current_user_id
        - g.current_user_email
    """
    db = SessionLocal()
    try:
        # Get user ID from JWT payload (injected by @require_auth)
        user_id = g.current_user_id

        # Find user in database
        user_repo = SQLAlchemyUserRepository(db)
        user = user_repo.find_by_id(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'id': str(user.id),
            'email': user.email,
            'display_name': user.display_name,
            'email_verified': user.email_verified,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch user: {str(e)}'}), 500

    finally:
        db.close()
