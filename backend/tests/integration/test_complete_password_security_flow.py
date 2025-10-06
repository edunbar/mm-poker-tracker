"""
End-to-end tests for complete password security workflows.

Tests cover full user journeys including registration, login,
password changes, session invalidation, and audit logging.
"""

import pytest
from sqlalchemy import text
from db.database import engine
from db.models import User, AuditLog


class TestCompletePasswordSecurityFlow:
    """Test complete password security workflows end-to-end."""

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

    def test_complete_password_change_workflow(self, test_client, auth_headers, db_session):
        """
        Test complete workflow:
        1. Register user
        2. Login and get token1
        3. Access protected endpoint with token1
        4. Change password
        5. Verify token1 invalid
        6. Login with new password
        7. Access protected endpoint with new token
        8. Verify audit log created
        9. Verify token_version incremented
        """
        # 1. Register user with strong password
        response = test_client.post('/api/auth/register', json={
            'email': 'workflow@example.com',
            'password': 'InitialPassword123!',
            'display_name': 'Workflow Test'
        })

        assert response.status_code == 201
        data = response.get_json()
        user_id = data['user']['id']
        token1 = data['access_token']

        # 2. Verify token1 works
        response = test_client.get('/api/auth/me', headers=auth_headers(token1))
        assert response.status_code == 200

        # Check initial token_version
        user = db_session.query(User).filter(User.id == user_id).first()
        initial_version = user.token_version
        assert initial_version == 1

        # 3. Change password
        response = test_client.patch('/api/auth/password',
            headers=auth_headers(token1),
            json={
                'current_password': 'InitialPassword123!',
                'new_password': 'NewPassword456!'
            }
        )

        assert response.status_code == 200

        # 4. Verify token1 is now invalid
        response = test_client.get('/api/auth/me', headers=auth_headers(token1))
        assert response.status_code == 401

        # 5. Login with new password
        response = test_client.post('/api/auth/login', json={
            'email': 'workflow@example.com',
            'password': 'NewPassword456!'
        })

        assert response.status_code == 200
        token2 = response.get_json()['access_token']

        # 6. Verify token2 works
        response = test_client.get('/api/auth/me', headers=auth_headers(token2))
        assert response.status_code == 200
        assert response.get_json()['email'] == 'workflow@example.com'

        # 7. Verify audit log was created
        audit_logs = db_session.query(AuditLog).filter(
            AuditLog.action == 'PASSWORD_CHANGED',
            AuditLog.user_id == user_id
        ).all()

        assert len(audit_logs) > 0
        audit = audit_logs[0]
        assert audit.after['success'] is True

        # 8. Verify token_version was incremented
        db_session.expire(user)  # Refresh from database
        user = db_session.query(User).filter(User.id == user_id).first()
        assert user.token_version == initial_version + 1

    def test_multiple_concurrent_sessions_invalidation(self, test_client, auth_headers):
        """
        Test that multiple concurrent sessions are all invalidated:
        1. Login 3 times → get 3 tokens
        2. All 3 tokens work
        3. Change password
        4. All 3 tokens invalid
        5. New login creates token4 that works
        """
        # Register user
        response = test_client.post('/api/auth/register', json={
            'email': 'multi@example.com',
            'password': 'Password123!',
            'display_name': 'Multi Session'
        })

        # Login 3 times to get 3 different tokens
        tokens = []
        for _ in range(3):
            response = test_client.post('/api/auth/login', json={
                'email': 'multi@example.com',
                'password': 'Password123!'
            })
            tokens.append(response.get_json()['access_token'])

        # Verify all tokens work
        for token in tokens:
            response = test_client.get('/api/auth/me', headers=auth_headers(token))
            assert response.status_code == 200

        # Change password using first token
        response = test_client.patch('/api/auth/password',
            headers=auth_headers(tokens[0]),
            json={
                'current_password': 'Password123!',
                'new_password': 'NewPassword456!'
            }
        )

        assert response.status_code == 200

        # All tokens should now be invalid
        for token in tokens:
            response = test_client.get('/api/auth/me', headers=auth_headers(token))
            assert response.status_code == 401

        # New login should work
        response = test_client.post('/api/auth/login', json={
            'email': 'multi@example.com',
            'password': 'NewPassword456!'
        })

        assert response.status_code == 200
        new_token = response.get_json()['access_token']

        # New token should work
        response = test_client.get('/api/auth/me', headers=auth_headers(new_token))
        assert response.status_code == 200

    def test_password_strength_prevents_weak_registrations(self, test_client):
        """
        Test that weak passwords are rejected during registration.
        Note: This test verifies password validation integration.
        """
        # Try to register with weak password (too short, no uppercase, no numbers)
        response = test_client.post('/api/auth/register', json={
            'email': 'weak@example.com',
            'password': 'weak',
            'display_name': 'Weak Password'
        })

        # Should be rejected (likely 400 error)
        assert response.status_code in [400, 401, 422]
        data = response.get_json()
        assert 'error' in data

        # Strong password should work
        response = test_client.post('/api/auth/register', json={
            'email': 'strong@example.com',
            'password': 'StrongPassword123!',
            'display_name': 'Strong Password'
        })

        assert response.status_code == 201
        assert 'access_token' in response.get_json()
