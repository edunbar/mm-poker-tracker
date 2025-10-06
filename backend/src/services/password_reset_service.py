"""
Password Reset Service

Provides secure password reset functionality using time-limited tokens.
Supports requesting a reset, validating tokens, and resetting passwords.
"""

import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

from db.models import User
from infrastructure.security import BcryptPasswordHasher
from services.email_service import send_password_reset_email
from services.audit_service import log_security_event


# Token configuration
TOKEN_EXPIRY_HOURS = 24
TOKEN_BYTES = 32  # 256 bits of entropy


def _hash_token(token: str) -> str:
    """
    Hash a reset token using SHA256.

    Tokens are stored hashed in the database for security.
    Even if the database is compromised, attackers cannot use stored tokens.

    Args:
        token: Plain text reset token

    Returns:
        Hex-encoded SHA256 hash of the token
    """
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def request_password_reset(email: str, ip_address: Optional[str], db_session: Session) -> bool:
    """
    Request a password reset for the given email address.

    Generates a secure reset token, saves it to the database, and sends
    an email with reset instructions. Always returns True to prevent
    email enumeration attacks.

    Security Notes:
        - Always returns True even if email doesn't exist (prevent enumeration)
        - Generates cryptographically secure random tokens
        - Tokens are stored hashed in database
        - Tokens expire after 24 hours
        - Rate limiting should be applied at the route level

    Args:
        email: Email address requesting password reset
        ip_address: IP address of requester (for audit trail)
        db_session: Database session

    Returns:
        Always returns True (to prevent email enumeration)
    """
    try:
        # Find user by email (case-insensitive)
        user = db_session.query(User).filter(User.email == email.lower()).first()

        if not user:
            # Don't reveal that email doesn't exist (prevent enumeration)
            # Still return True but don't send email
            return True

        # Generate secure random token (32 bytes = 256 bits)
        reset_token = secrets.token_urlsafe(TOKEN_BYTES)

        # Hash token for storage
        token_hash = _hash_token(reset_token)

        # Calculate expiry time
        expires_at = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS)

        # Store token in database
        db_session.execute(
            text("""
                INSERT INTO password_reset_tokens
                (user_id, token_hash, expires_at, ip_address)
                VALUES (:user_id, :token_hash, :expires_at, :ip_address)
            """),
            {
                'user_id': user.id,
                'token_hash': token_hash,
                'expires_at': expires_at,
                'ip_address': ip_address
            }
        )
        db_session.commit()

        # Send reset email with plain token (not hashed)
        send_password_reset_email(user.email, user.display_name, reset_token)

        # Log security event
        log_security_event(
            action='PASSWORD_RESET_REQUESTED',
            user_id=str(user.id),
            user_email=user.email,
            details={
                'ip_address': ip_address,
                'expires_at': expires_at.isoformat()
            }
        )

        return True

    except Exception as e:
        db_session.rollback()
        # Log error but still return True (prevent enumeration)
        print(f"Error in request_password_reset: {e}")
        return True


def validate_reset_token(token: str, db_session: Session) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate a password reset token.

    Checks if the token exists, hasn't expired, and hasn't been used.

    Args:
        token: Plain text reset token from email link
        db_session: Database session

    Returns:
        Tuple of (is_valid, user_id, error_message)
        - is_valid: True if token is valid
        - user_id: User ID if token is valid, None otherwise
        - error_message: Error description if invalid, None otherwise
    """
    try:
        print(f"[DEBUG] validate_reset_token called with token: {token[:20]}...")

        # Hash the provided token
        token_hash = _hash_token(token)
        print(f"[DEBUG] Token hash: {token_hash}")

        # Find token in database
        result = db_session.execute(
            text("""
                SELECT user_id, expires_at, used_at
                FROM password_reset_tokens
                WHERE token_hash = :token_hash
                LIMIT 1
            """),
            {'token_hash': token_hash}
        ).first()

        print(f"[DEBUG] Database query result: {result}")

        if not result:
            print("[DEBUG] Token not found in database")
            return False, None, "Invalid or expired reset token"

        user_id, expires_at, used_at = result
        print(f"[DEBUG] Token found - user_id: {user_id}, expires_at: {expires_at}, used_at: {used_at}")

        # Check if already used
        if used_at is not None:
            print("[DEBUG] Token already used")
            return False, None, "This reset link has already been used"

        # Check if expired
        current_time = datetime.now(timezone.utc)
        print(f"[DEBUG] Current time: {current_time}, Expires at: {expires_at}")
        if current_time > expires_at:
            print("[DEBUG] Token expired")
            return False, None, "This reset link has expired. Please request a new one"

        # Token is valid
        print("[DEBUG] Token is valid!")
        return True, str(user_id), None

    except Exception as e:
        print(f"[ERROR] Error in validate_reset_token: {e}")
        import traceback
        traceback.print_exc()
        return False, None, "Failed to validate reset token"


def reset_password_with_token(
    token: str,
    new_password: str,
    ip_address: Optional[str],
    db_session: Session
) -> Tuple[bool, Optional[str]]:
    """
    Reset a user's password using a valid reset token.

    Validates the token, updates the password, invalidates all sessions,
    marks the token as used, and sends a confirmation email.

    Security Notes:
        - Password is hashed with bcrypt
        - token_version is incremented to invalidate all existing sessions
        - Token is marked as used (cannot be reused)
        - Audit log is created
        - Confirmation email is sent

    Args:
        token: Plain text reset token from email link
        new_password: New password (will be hashed)
        ip_address: IP address of requester (for audit trail)
        db_session: Database session

    Returns:
        Tuple of (success, error_message)
        - success: True if password was reset successfully
        - error_message: Error description if failed, None on success
    """
    try:
        # Validate token first
        is_valid, user_id, error_message = validate_reset_token(token, db_session)

        if not is_valid:
            return False, error_message

        # Find user
        user = db_session.query(User).filter(User.id == user_id).first()

        if not user:
            return False, "User not found"

        # Hash new password
        password_hasher = BcryptPasswordHasher()
        new_password_hash = password_hasher.hash(new_password)

        # Update user password
        user.password_hash = new_password_hash

        # Increment token_version to invalidate all existing sessions
        user.token_version += 1

        # Mark token as used
        token_hash = _hash_token(token)
        db_session.execute(
            text("""
                UPDATE password_reset_tokens
                SET used_at = :used_at
                WHERE token_hash = :token_hash
            """),
            {
                'used_at': datetime.now(timezone.utc),
                'token_hash': token_hash
            }
        )

        db_session.commit()

        # Log security event
        log_security_event(
            action='PASSWORD_RESET_COMPLETED',
            user_id=str(user.id),
            user_email=user.email,
            details={
                'ip_address': ip_address,
                'method': 'email_token_reset'
            }
        )

        # Send confirmation email (imported function already exists)
        from services.email_service import send_password_changed_notification
        send_password_changed_notification(user.email, user.display_name)

        return True, None

    except Exception as e:
        db_session.rollback()
        print(f"Error in reset_password_with_token: {e}")
        return False, f"Failed to reset password: {str(e)}"


def cleanup_expired_tokens(db_session: Session) -> int:
    """
    Clean up expired password reset tokens from the database.

    Should be called periodically (e.g., daily cron job) to remove old tokens.

    Args:
        db_session: Database session

    Returns:
        Number of tokens deleted
    """
    try:
        result = db_session.execute(
            text("""
                DELETE FROM password_reset_tokens
                WHERE expires_at < :now
            """),
            {'now': datetime.now(timezone.utc)}
        )
        db_session.commit()
        return result.rowcount

    except Exception as e:
        db_session.rollback()
        print(f"Error in cleanup_expired_tokens: {e}")
        return 0
