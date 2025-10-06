"""
Integration tests for password reset flow.

Tests cover the complete password reset workflow including:
- Requesting a password reset
- Validating reset tokens
- Resetting passwords
- Security features (token expiry, single-use, session invalidation)
"""

import pytest
import secrets
import hashlib
from datetime import datetime, timedelta
from sqlalchemy import text
from unittest.mock import patch

from db.database import engine
from db.models import User
from services.password_reset_service import (
    request_password_reset,
    validate_reset_token,
    reset_password_with_token,
    _hash_token
)


class TestPasswordResetFlow:
    """Test complete password reset workflow."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clean database before and after each test."""
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM password_reset_tokens CASCADE"))
            conn.execute(text("DELETE FROM audit_log CASCADE"))
            conn.execute(text("DELETE FROM games CASCADE"))
            conn.execute(text("DELETE FROM users CASCADE"))
            conn.commit()

        yield

        with engine.connect() as conn:
            conn.execute(text("DELETE FROM password_reset_tokens CASCADE"))
            conn.execute(text("DELETE FROM audit_log CASCADE"))
            conn.execute(text("DELETE FROM games CASCADE"))
            conn.execute(text("DELETE FROM users CASCADE"))
            conn.commit()

    @patch('services.password_reset_service.send_password_reset_email')
    def test_complete_password_reset_flow(self, mock_send_email, register_user, auth_headers, db_session):
        """
        Test complete password reset workflow:
        1. User requests password reset
        2. Token is generated and stored
        3. User receives email with reset link
        4. User resets password with token
        5. Old sessions are invalidated
        6. User can login with new password
        """
        # 1. Register user
        user, old_token = register_user('test@example.com', 'OldPassword123!', 'Test User')

        # Verify old token works
        db_user = db_session.query(User).filter(User.email == 'test@example.com').first()
        initial_token_version = db_user.token_version

        # 2. Request password reset
        success = request_password_reset('test@example.com', '127.0.0.1', db_session)
        assert success is True
        assert mock_send_email.called

        # Get the reset token from the mock call
        call_args = mock_send_email.call_args
        reset_token = call_args[0][2]  # Third argument is the token
        assert reset_token is not None

        # 3. Validate token
        is_valid, user_id, error = validate_reset_token(reset_token, db_session)
        assert is_valid is True
        assert user_id == user['id']
        assert error is None

        # 4. Reset password
        success, error = reset_password_with_token(
            reset_token,
            'NewPassword456!',
            '127.0.0.1',
            db_session
        )
        assert success is True
        assert error is None

        # 5. Verify token_version was incremented
        db_session.expire_all()
        db_user = db_session.query(User).filter(User.email == 'test@example.com').first()
        assert db_user.token_version == initial_token_version + 1

        # 6. Verify password was changed (can't login with old password)
        from infrastructure.security import BcryptPasswordHasher
        password_hasher = BcryptPasswordHasher()
        assert not password_hasher.verify('OldPassword123!', db_user.password_hash)
        assert password_hasher.verify('NewPassword456!', db_user.password_hash)

    @patch('services.password_reset_service.send_password_reset_email')
    def test_request_reset_for_nonexistent_email_returns_success(self, mock_send_email, db_session):
        """Test that requesting reset for non-existent email returns success (prevent enumeration)."""
        success = request_password_reset('nonexistent@example.com', '127.0.0.1', db_session)

        # Should return True to prevent email enumeration
        assert success is True

        # Should NOT send email
        assert not mock_send_email.called

    @patch('services.password_reset_service.send_password_reset_email')
    def test_expired_token_is_rejected(self, mock_send_email, register_user, db_session):
        """Test that expired tokens are rejected."""
        # Register user and request reset
        user, _ = register_user('test@example.com', 'Password123!', 'Test User')
        request_password_reset('test@example.com', '127.0.0.1', db_session)

        # Get the token from mock
        reset_token = mock_send_email.call_args[0][2]

        # Manually expire the token in database
        token_hash = _hash_token(reset_token)
        db_session.execute(
            text("""
                UPDATE password_reset_tokens
                SET expires_at = :expired_time
                WHERE token_hash = :token_hash
            """),
            {
                'expired_time': datetime.utcnow() - timedelta(hours=1),
                'token_hash': token_hash
            }
        )
        db_session.commit()

        # Try to validate expired token
        is_valid, user_id, error = validate_reset_token(reset_token, db_session)
        assert is_valid is False
        assert user_id is None
        assert 'expired' in error.lower()

    @patch('services.password_reset_service.send_password_reset_email')
    def test_used_token_is_rejected(self, mock_send_email, register_user, db_session):
        """Test that already-used tokens are rejected."""
        # Register user and request reset
        user, _ = register_user('test@example.com', 'Password123!', 'Test User')
        request_password_reset('test@example.com', '127.0.0.1', db_session)

        # Get the token from mock
        reset_token = mock_send_email.call_args[0][2]

        # Use the token once
        success, error = reset_password_with_token(reset_token, 'NewPassword456!', '127.0.0.1', db_session)
        assert success is True

        # Try to use the same token again
        is_valid, user_id, error = validate_reset_token(reset_token, db_session)
        assert is_valid is False
        assert user_id is None
        assert 'already been used' in error

    @patch('services.password_reset_service.send_password_reset_email')
    def test_invalid_token_is_rejected(self, mock_send_email, register_user, db_session):
        """Test that invalid/non-existent tokens are rejected."""
        # Register user
        user, _ = register_user('test@example.com', 'Password123!', 'Test User')

        # Try to validate a fake token
        fake_token = secrets.token_urlsafe(32)
        is_valid, user_id, error = validate_reset_token(fake_token, db_session)
        assert is_valid is False
        assert user_id is None
        assert 'Invalid' in error or 'expired' in error

    @patch('services.password_reset_service.send_password_reset_email')
    def test_token_is_stored_hashed(self, mock_send_email, register_user, db_session):
        """Test that tokens are stored hashed in database for security."""
        # Register user and request reset
        user, _ = register_user('test@example.com', 'Password123!', 'Test User')
        request_password_reset('test@example.com', '127.0.0.1', db_session)

        # Get the plain token from mock
        plain_token = mock_send_email.call_args[0][2]

        # Check that database contains hashed version, not plain
        result = db_session.execute(
            text("SELECT token_hash FROM password_reset_tokens LIMIT 1")
        ).first()

        stored_hash = result[0]

        # Verify it's a hash (64 hex chars = SHA256)
        assert len(stored_hash) == 64
        assert stored_hash != plain_token

        # Verify it matches our hash function
        expected_hash = hashlib.sha256(plain_token.encode('utf-8')).hexdigest()
        assert stored_hash == expected_hash

    @patch('services.password_reset_service.send_password_reset_email')
    def test_password_reset_creates_audit_log(self, mock_send_email, register_user, db_session):
        """Test that password reset creates audit log entries."""
        from db.models import AuditLog

        # Register user and request reset
        user, _ = register_user('test@example.com', 'Password123!', 'Test User')
        request_password_reset('test@example.com', '127.0.0.1', db_session)

        # Get the token and reset password
        reset_token = mock_send_email.call_args[0][2]
        reset_password_with_token(reset_token, 'NewPassword456!', '127.0.0.1', db_session)

        # Check audit logs
        audit_logs = db_session.query(AuditLog).filter(
            AuditLog.action.in_(['PASSWORD_RESET_REQUESTED', 'PASSWORD_RESET_COMPLETED'])
        ).all()

        assert len(audit_logs) >= 2  # At least request and completion

        # Verify request log
        request_log = next((log for log in audit_logs if log.action == 'PASSWORD_RESET_REQUESTED'), None)
        assert request_log is not None
        assert str(request_log.user_id) == user['id']

        # Verify completion log
        completion_log = next((log for log in audit_logs if log.action == 'PASSWORD_RESET_COMPLETED'), None)
        assert completion_log is not None
        assert str(completion_log.user_id) == user['id']
        assert completion_log.after['method'] == 'email_token_reset'

    @patch('services.password_reset_service.send_password_reset_email')
    def test_multiple_reset_requests_create_multiple_tokens(self, mock_send_email, register_user, db_session):
        """Test that multiple reset requests create multiple tokens (all valid)."""
        # Register user
        user, _ = register_user('test@example.com', 'Password123!', 'Test User')

        # Request reset twice
        request_password_reset('test@example.com', '127.0.0.1', db_session)
        token1 = mock_send_email.call_args[0][2]

        request_password_reset('test@example.com', '127.0.0.1', db_session)
        token2 = mock_send_email.call_args[0][2]

        # Both tokens should be valid
        is_valid1, _, _ = validate_reset_token(token1, db_session)
        is_valid2, _, _ = validate_reset_token(token2, db_session)

        assert is_valid1 is True
        assert is_valid2 is True
        assert token1 != token2

        # Using one token shouldn't invalidate the other
        success, _ = reset_password_with_token(token1, 'NewPassword456!', '127.0.0.1', db_session)
        assert success is True

        # token1 should be used, token2 should still be valid
        is_valid1, _, _ = validate_reset_token(token1, db_session)
        is_valid2, _, _ = validate_reset_token(token2, db_session)

        assert is_valid1 is False  # Already used
        assert is_valid2 is True  # Still valid

    @patch('services.password_reset_service.send_password_reset_email')
    def test_reset_password_sends_confirmation_email(self, mock_send_email, register_user, db_session):
        """Test that resetting password sends confirmation email."""
        from services.email_service import send_password_changed_notification

        with patch('services.password_reset_service.send_password_changed_notification') as mock_confirm:
            # Register user and request reset
            user, _ = register_user('test@example.com', 'Password123!', 'Test User')
            request_password_reset('test@example.com', '127.0.0.1', db_session)

            # Reset password
            reset_token = mock_send_email.call_args[0][2]
            reset_password_with_token(reset_token, 'NewPassword456!', '127.0.0.1', db_session)

            # Verify confirmation email was sent
            assert mock_confirm.called
            call_args = mock_confirm.call_args[0]
            assert call_args[0] == 'test@example.com'
            assert call_args[1] == 'Test User'
