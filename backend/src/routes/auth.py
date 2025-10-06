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
from services.email_service import send_password_changed_notification
from services.audit_service import log_security_event
from services.password_strength_service import calculate_password_strength, get_password_requirements

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
        - Minimum 8 characters
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
            user.email,
            user.token_version
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
            "password": "SecurePassword123!",
            "remember_me": false  // optional, defaults to false
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
        - remember_me=true sets token expiry to 30 days, false sets 7 days
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
        remember_me = data.get('remember_me', False)

        # Create authentication service
        auth_service = get_auth_service(db)

        # Authenticate user (returns Result[User])
        result = auth_service.login(email, password)

        # Handle failure (generic error for security)
        if result.is_failure():
            return jsonify({'error': 'Invalid credentials'}), 401

        # Success - get user and generate JWT
        user = result.value  # SQLAlchemy User model

        # Get JWT secret
        jwt_secret = os.environ.get('JWT_SECRET')
        if not jwt_secret:
            raise RuntimeError(
                "JWT_SECRET environment variable not configured. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )

        # Create token service with expiry based on remember_me
        token_expiry_days = 30 if remember_me else 7
        token_service = JWTTokenService(secret_key=jwt_secret, token_expiry_days=token_expiry_days)

        access_token = token_service.generate_access_token(
            str(user.id),
            user.email,
            user.token_version
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


@auth_bp.route('/profile', methods=['PATCH'])
@require_auth
def update_profile():
    """
    Update current authenticated user's profile.

    Headers:
        Authorization: Bearer <jwt_token>

    Request Body:
        {
            "display_name": "New Display Name"
        }

    Returns:
        200: {
            "user": {
                "id": "uuid",
                "email": "user@example.com",
                "display_name": "New Display Name"
            }
        }

        400: { "error": "validation error message" }
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
        # Parse request
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        # Validate required fields
        if 'display_name' not in data:
            return jsonify({'error': 'Missing required field: display_name'}), 400

        display_name = data['display_name'].strip()

        # Validate length
        if len(display_name) < 2:
            return jsonify({'error': 'Display name must be at least 2 characters'}), 400
        if len(display_name) > 50:
            return jsonify({'error': 'Display name must not exceed 50 characters'}), 400

        if not display_name:
            return jsonify({'error': 'Display name cannot be empty'}), 400

        # Get user ID from JWT payload (injected by @require_auth)
        user_id = g.current_user_id

        # Find user in database
        user_repo = SQLAlchemyUserRepository(db)
        user = user_repo.find_by_id(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Update display name
        user.display_name = display_name
        db.commit()

        return jsonify({
            'user': {
                'id': str(user.id),
                'email': user.email,
                'display_name': user.display_name
            }
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to update profile: {str(e)}'}), 500

    finally:
        db.close()


@auth_bp.route('/password', methods=['PATCH'])
@require_auth
def change_password():
    """
    Change current authenticated user's password.

    Headers:
        Authorization: Bearer <jwt_token>

    Request Body:
        {
            "current_password": "OldPassword123!",
            "new_password": "NewSecurePassword456!"
        }

    Returns:
        200: { "message": "Password updated successfully" }

        400: { "error": "validation error message" }
            - Missing fields
            - New password same as current
            - Password length requirements (8-72 chars)
        401: { "error": "Current password is incorrect" }
        404: { "error": "User not found" }
        500: { "error": "server error message" }

    Note:
        Requires valid JWT token in Authorization header.
        Password requirements:
        - Minimum 8 characters
        - Maximum 72 characters (bcrypt limit)
        - Must be different from current password
    """
    db = SessionLocal()
    try:
        # Parse request
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        # Validate required fields
        if 'current_password' not in data:
            return jsonify({'error': 'Missing required field: current_password'}), 400
        if 'new_password' not in data:
            return jsonify({'error': 'Missing required field: new_password'}), 400

        current_password = data['current_password']
        new_password = data['new_password']

        # Validate new password length
        if len(new_password) < 8:
            return jsonify({'error': 'New password must be at least 8 characters'}), 400
        if len(new_password) > 72:
            return jsonify({'error': 'New password must not exceed 72 characters'}), 400

        # Check new password is different from current
        if current_password == new_password:
            return jsonify({'error': 'New password must be different from current password'}), 400

        # Get user ID from JWT payload (injected by @require_auth)
        user_id = g.current_user_id

        # Find user in database
        user_repo = SQLAlchemyUserRepository(db)
        user = user_repo.find_by_id(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Verify current password
        password_hasher = BcryptPasswordHasher()
        if not password_hasher.verify(current_password, user.password_hash):
            return jsonify({'error': 'Current password is incorrect'}), 401

        # Hash new password and update
        new_password_hash = password_hasher.hash(new_password)
        user.password_hash = new_password_hash

        # Increment token_version to invalidate all existing sessions
        user.token_version += 1

        db.commit()

        # Log security event
        log_security_event(
            action='PASSWORD_CHANGED',
            user_id=str(user.id),
            user_email=user.email,
            details={
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', 'Unknown'),
                'method': 'authenticated_change'
            }
        )

        # Send password changed notification email (non-blocking)
        send_password_changed_notification(user.email, user.display_name)

        return jsonify({'message': 'Password updated successfully'}), 200

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to update password: {str(e)}'}), 500

    finally:
        db.close()


@auth_bp.route('/account', methods=['DELETE'])
@require_auth
def delete_account():
    """
    Delete current authenticated user's account.

    Headers:
        Authorization: Bearer <jwt_token>

    Request Body:
        {
            "password": "UserPassword123!",
            "confirmation": "DELETE"
        }

    Returns:
        200: { "message": "Account deleted successfully" }

        400: { "error": "validation error message" }
            - Missing fields
            - Confirmation text not exactly "DELETE"
        401: { "error": "Incorrect password" }
        404: { "error": "User not found" }
        500: { "error": "server error message" }

    Note:
        Requires valid JWT token in Authorization header.
        This action is IRREVERSIBLE.
        - User account will be permanently deleted
        - Games owned by user will be orphaned (owner_user_id set to NULL)
        - Poker identity claims will be cascade deleted
        - Confirmation must be exactly "DELETE" (case-sensitive)
    """
    db = SessionLocal()
    try:
        # Parse request
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        # Validate required fields
        if 'password' not in data:
            return jsonify({'error': 'Missing required field: password'}), 400
        if 'confirmation' not in data:
            return jsonify({'error': 'Missing required field: confirmation'}), 400

        password = data['password']
        confirmation = data['confirmation']

        # Validate confirmation text (case-sensitive)
        if confirmation != 'DELETE':
            return jsonify({'error': 'Confirmation must be exactly "DELETE"'}), 400

        # Get user ID from JWT payload (injected by @require_auth)
        user_id = g.current_user_id

        # Find user in database
        user_repo = SQLAlchemyUserRepository(db)
        user = user_repo.find_by_id(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Verify password
        password_hasher = BcryptPasswordHasher()
        if not password_hasher.verify(password, user.password_hash):
            return jsonify({'error': 'Incorrect password'}), 401

        # Delete user (games will be orphaned via SET NULL, poker_identities cascade delete)
        db.delete(user)
        db.commit()

        return jsonify({'message': 'Account deleted successfully'}), 200

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to delete account: {str(e)}'}), 500

    finally:
        db.close()


@auth_bp.route('/password-strength', methods=['POST'])
def check_password_strength():
    """
    Check password strength and return feedback.

    Request Body:
        {
            "password": "ExamplePassword123!"
        }

    Returns:
        200: {
            "score": 85,
            "strength": "strong",
            "feedback": ["Your password is strong!"],
            "meets_requirements": true,
            "details": {
                "length": 20,
                "has_lowercase": true,
                "has_uppercase": true,
                "has_numbers": true,
                "has_special": true,
                "is_common": false
            }
        }

        400: { "error": "validation error message" }

    Note:
        This endpoint is public and does not require authentication.
        Rate limited to prevent abuse.
    """
    try:
        # Parse request
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        if 'password' not in data:
            return jsonify({'error': 'Missing required field: password'}), 400

        password = data['password']

        # Calculate password strength
        result = calculate_password_strength(password)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': f'Failed to check password strength: {str(e)}'}), 500


@auth_bp.route('/password-requirements', methods=['GET'])
def get_requirements():
    """
    Get password requirements for the application.

    Returns:
        200: {
            "min_length": 8,
            "max_length": 72,
            "requires_lowercase": true,
            "requires_uppercase": true,
            "requires_numbers": true,
            "requires_special": false,
            "disallow_common": true
        }

    Note:
        This endpoint is public and does not require authentication.
    """
    try:
        requirements = get_password_requirements()
        return jsonify(requirements), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get password requirements: {str(e)}'}), 500


@auth_bp.route('/forgot-password', methods=['POST'])
@limiter.limit("3 per hour")
def forgot_password():
    """
    Request a password reset email.

    Generates a secure reset token, stores it in the database, and sends
    an email with reset instructions. Always returns 200 to prevent email
    enumeration attacks.

    Request Body:
        {
            "email": "user@example.com"
        }

    Returns:
        200: {
            "message": "If an account exists with that email, you will receive password reset instructions."
        }

    Security Notes:
        - Rate limited to 3 requests per hour per IP
        - Always returns success (prevents email enumeration)
        - Tokens expire after 24 hours
        - Tokens are stored hashed in database
        - Email is only sent if account exists
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

        email = data['email'].strip().lower()

        # Validate email format
        if not email or '@' not in email:
            return jsonify({'error': 'Invalid email address'}), 400

        # Get IP address for audit trail
        ip_address = request.remote_addr

        # Import password reset service
        from services.password_reset_service import request_password_reset

        # Request password reset (always returns True)
        request_password_reset(email, ip_address, db)

        # Always return success message (prevent email enumeration)
        return jsonify({
            'message': 'If an account exists with that email, you will receive password reset instructions.'
        }), 200

    except Exception as e:
        # Log error but still return success (prevent enumeration)
        print(f"Error in forgot_password: {e}")
        return jsonify({
            'message': 'If an account exists with that email, you will receive password reset instructions.'
        }), 200

    finally:
        db.close()


@auth_bp.route('/reset-password', methods=['POST'])
@limiter.limit("5 per hour")
def reset_password():
    """
    Reset password using a valid reset token.

    Validates the token, updates the password, invalidates all sessions,
    marks the token as used, and sends a confirmation email.

    Request Body:
        {
            "token": "secure_reset_token_from_email",
            "new_password": "NewSecurePassword456!"
        }

    Returns:
        200: { "message": "Password reset successful. You can now log in with your new password." }

        400: { "error": "validation or token error message" }
            - Missing fields
            - Invalid/expired/used token
            - Password validation errors

    Security Notes:
        - Rate limited to 5 requests per hour per IP
        - Tokens are single-use and expire after 24 hours
        - Password strength is validated
        - All existing sessions are invalidated (token_version incremented)
        - Audit log is created
        - Confirmation email is sent
    """
    db = SessionLocal()
    try:
        # Parse request
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        # Validate required fields
        if 'token' not in data:
            return jsonify({'error': 'Missing required field: token'}), 400
        if 'new_password' not in data:
            return jsonify({'error': 'Missing required field: new_password'}), 400

        token = data['token'].strip()
        new_password = data['new_password']

        # Validate password length
        if len(new_password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        if len(new_password) > 72:
            return jsonify({'error': 'Password must not exceed 72 characters'}), 400

        # Get IP address for audit trail
        ip_address = request.remote_addr

        # Import password reset service
        from services.password_reset_service import reset_password_with_token

        # Reset password with token
        success, error_message = reset_password_with_token(token, new_password, ip_address, db)

        if not success:
            return jsonify({'error': error_message}), 400

        return jsonify({
            'message': 'Password reset successful. You can now log in with your new password.'
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to reset password: {str(e)}'}), 500

    finally:
        db.close()
