"""
Integration tests for password change security features.

Tests cover token_version incrementing, session invalidation,
security audit logging, and email notifications when passwords are changed.
"""

import pytest
from sqlalchemy import text
from unittest.mock import patch
from db.database import engine
from db.models import User, AuditLog


class TestPasswordChangeSecurity:
    """Test password change security integration."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clean database before and after each test."""
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM audit_log CASCADE"))
            conn.execute(text("DELETE FROM games CASCADE"))
            conn.execute(text("DELETE FROM users CASCADE"))
            conn.commit()

        yield

        with engine.connect() as conn:
            conn.execute(text("DELETE FROM audit_log CASCADE"))
            conn.execute(text("DELETE FROM games CASCADE"))
            conn.execute(text("DELETE FROM users CASCADE"))
            conn.commit()

    def test_password_change_increments_token_version(self, test_client, register_user, auth_headers, db_session):
        """Test that changing password increments token_version in database."""
        # Register user
        user, token = register_user('test@example.com', 'OldPassword123!', 'Test User')

        # Get initial token_version
        db_user = db_session.query(User).filter(User.email == 'test@example.com').first()
        initial_version = db_user.token_version

        # Change password
        response = test_client.patch('/api/auth/password',
            headers=auth_headers(token),
            json={
                'current_password': 'OldPassword123!',
                'new_password': 'NewPassword456!'
            }
        )

        assert response.status_code == 200

        # Verify token_version was incremented
        db_session.expire(db_user)  # Refresh from database
        db_user = db_session.query(User).filter(User.email == 'test@example.com').first()
        assert db_user.token_version == initial_version + 1

    def test_old_token_invalid_after_password_change(self, test_client, register_user, auth_headers):
        """Test that old JWT token is invalidated after password change."""
        # Register user
        user, old_token = register_user('test@example.com', 'OldPassword123!', 'Test User')

        # Verify old token works
        response = test_client.get('/api/auth/me', headers=auth_headers(old_token))
        assert response.status_code == 200

        # Change password
        response = test_client.patch('/api/auth/password',
            headers=auth_headers(old_token),
            json={
                'current_password': 'OldPassword123!',
                'new_password': 'NewPassword456!'
            }
        )

        assert response.status_code == 200

        # Try using old token - should be rejected
        response = test_client.get('/api/auth/me', headers=auth_headers(old_token))
        assert response.status_code == 401
        data = response.get_json()
        assert 'session expired' in data['error'].lower() or 'log in again' in data['error'].lower()

    def test_new_login_works_after_password_change(self, test_client, register_user, auth_headers):
        """Test that new login with new password works after change."""
        # Register user
        user, old_token = register_user('test@example.com', 'OldPassword123!', 'Test User')

        # Change password
        response = test_client.patch('/api/auth/password',
            headers=auth_headers(old_token),
            json={
                'current_password': 'OldPassword123!',
                'new_password': 'NewPassword456!'
            }
        )

        assert response.status_code == 200

        # Login with new password
        response = test_client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'NewPassword456!'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data

        new_token = data['access_token']

        # Verify new token works
        response = test_client.get('/api/auth/me', headers=auth_headers(new_token))
        assert response.status_code == 200

    def test_multiple_sessions_all_invalidated(self, test_client, register_user, auth_headers):
        """Test that all existing tokens are invalidated after password change."""
        # Register user and get multiple tokens
        user, token1 = register_user('test@example.com', 'OldPassword123!', 'Test User')

        # Login again to get second token
        response = test_client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'OldPassword123!'
        })
        token2 = response.get_json()['access_token']

        # Login third time
        response = test_client.post('/api/auth/login', json={
            'email': 'test@example.com',
            'password': 'OldPassword123!'
        })
        token3 = response.get_json()['access_token']

        # Verify all three tokens work
        assert test_client.get('/api/auth/me', headers=auth_headers(token1)).status_code == 200
        assert test_client.get('/api/auth/me', headers=auth_headers(token2)).status_code == 200
        assert test_client.get('/api/auth/me', headers=auth_headers(token3)).status_code == 200

        # Change password using token1
        response = test_client.patch('/api/auth/password',
            headers=auth_headers(token1),
            json={
                'current_password': 'OldPassword123!',
                'new_password': 'NewPassword456!'
            }
        )

        assert response.status_code == 200

        # All three tokens should now be invalid
        assert test_client.get('/api/auth/me', headers=auth_headers(token1)).status_code == 401
        assert test_client.get('/api/auth/me', headers=auth_headers(token2)).status_code == 401
        assert test_client.get('/api/auth/me', headers=auth_headers(token3)).status_code == 401

    def test_password_change_creates_audit_log(self, test_client, register_user, auth_headers, db_session):
        """Test that password change creates security audit log entry."""
        # Register user
        user, token = register_user('test@example.com', 'OldPassword123!', 'Test User')

        # Change password
        response = test_client.patch('/api/auth/password',
            headers=auth_headers(token),
            json={
                'current_password': 'OldPassword123!',
                'new_password': 'NewPassword456!'
            }
        )

        assert response.status_code == 200

        # Check for audit log entry
        audit_logs = db_session.query(AuditLog).filter(
            AuditLog.action == 'PASSWORD_CHANGED',
            AuditLog.actor_id == 'test@example.com'
        ).all()

        assert len(audit_logs) > 0
        audit_entry = audit_logs[0]

        # Verify audit log details
        assert audit_entry.user_id is not None
        assert str(audit_entry.user_id) == user['id']
        assert audit_entry.target_table == 'users'
        assert audit_entry.actor_kind == 'user'
        assert audit_entry.after is not None
        assert audit_entry.after['success'] is True
        assert 'ip_address' in audit_entry.after
        assert 'user_agent' in audit_entry.after

    @patch('services.email_service.SendGridAPIClient')
    @patch('services.email_service.os.getenv')
    def test_password_change_sends_notification_email(self, mock_getenv, mock_sendgrid_client,
                                                       test_client, register_user, auth_headers):
        """Test that password change triggers notification email."""
        from unittest.mock import MagicMock

        # Mock SendGrid
        mock_getenv.side_effect = lambda key, default=None: {
            'SENDGRID_API_KEY': 'test_key',
            'FROM_EMAIL': 'noreply@homegame.gg'
        }.get(key, default)

        mock_sg_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_sg_instance.send.return_value = mock_response
        mock_sendgrid_client.return_value = mock_sg_instance

        # Register user
        user, token = register_user('test@example.com', 'OldPassword123!', 'Test User')

        with patch('services.email_service.Mail') as mock_mail:
            # Change password
            response = test_client.patch('/api/auth/password',
                headers=auth_headers(token),
                json={
                    'current_password': 'OldPassword123!',
                    'new_password': 'NewPassword456!'
                }
            )

            assert response.status_code == 200

            # Verify Mail was created (email was sent)
            assert mock_mail.called

    def test_incorrect_current_password_rejected(self, test_client, register_user, auth_headers):
        """Test that incorrect current password is rejected."""
        # Register user
        user, token = register_user('test@example.com', 'OldPassword123!', 'Test User')

        # Try to change password with wrong current password
        response = test_client.patch('/api/auth/password',
            headers=auth_headers(token),
            json={
                'current_password': 'WrongPassword123!',
                'new_password': 'NewPassword456!'
            }
        )

        assert response.status_code == 401
        data = response.get_json()
        assert 'incorrect' in data['error'].lower()

    def test_password_change_requires_authentication(self, test_client):
        """Test that password change requires valid JWT token."""
        response = test_client.patch('/api/auth/password',
            json={
                'current_password': 'OldPassword123!',
                'new_password': 'NewPassword456!'
            }
        )

        assert response.status_code == 401

    def test_token_version_starts_at_one(self, test_client, register_user, db_session):
        """Test that newly registered users have token_version=1."""
        # Register user
        user, token = register_user('test@example.com', 'Password123!', 'Test User')

        # Check database
        db_user = db_session.query(User).filter(User.email == 'test@example.com').first()
        assert db_user.token_version == 1

    def test_multiple_password_changes_increment_version(self, test_client, register_user, auth_headers, db_session):
        """Test that multiple password changes continue incrementing version."""
        # Register user
        user, token1 = register_user('test@example.com', 'Password1!', 'Test User')

        passwords = ['Password2!', 'Password3!', 'Password4!']
        expected_version = 1

        for i, new_password in enumerate(passwords):
            # Get current token (login with current password)
            if i > 0:
                response = test_client.post('/api/auth/login', json={
                    'email': 'test@example.com',
                    'password': passwords[i-1]
                })
                token = response.get_json()['access_token']
            else:
                token = token1

            # Change password
            response = test_client.patch('/api/auth/password',
                headers=auth_headers(token),
                json={
                    'current_password': passwords[i-1] if i > 0 else 'Password1!',
                    'new_password': new_password
                }
            )

            assert response.status_code == 200
            expected_version += 1

            # Verify version incremented (refresh from database)
            db_session.expire_all()
            db_user = db_session.query(User).filter(User.email == 'test@example.com').first()
            assert db_user.token_version == expected_version
