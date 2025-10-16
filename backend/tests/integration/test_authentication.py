"""
Integration tests for authentication system.

Tests cover user registration, login, and protected route access
with JWT token authentication.
"""

import pytest
from sqlalchemy import text
from db.database import engine
from db.models import User


class TestAuthentication:
    """Test suite for authentication endpoints and JWT token handling."""

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

    def test_user_registration_success(self, test_client, db_session):
        """Test successful user registration with valid data."""
        response = test_client.post('/api/auth/register', json={
            'email': 'newuser@example.com',
            'password': 'SecurePassword123!',
            'display_name': 'New User'
        })

        assert response.status_code == 201
        data = response.get_json()

        # Verify response structure
        assert 'user' in data
        assert 'access_token' in data
        assert data['user']['email'] == 'newuser@example.com'
        assert data['user']['display_name'] == 'New User'
        assert 'id' in data['user']

        # Verify JWT token format (3 parts separated by dots)
        assert data['access_token'].count('.') == 2

        # Verify user exists in database
        user = db_session.query(User).filter(User.email == 'newuser@example.com').first()
        assert user is not None
        assert user.display_name == 'New User'
        assert user.email_verified is False

        # Verify password is hashed (starts with bcrypt prefix)
        assert user.password_hash.startswith('$2b$')
        assert user.password_hash != 'SecurePassword123!'

    def test_user_registration_duplicate_email(self, test_client):
        """Test registration fails with duplicate email."""
        # Register first user
        test_client.post('/api/auth/register', json={
            'email': 'duplicate@example.com',
            'password': 'Password123456!',
            'display_name': 'First User'
        })

        # Try to register with same email
        response = test_client.post('/api/auth/register', json={
            'email': 'duplicate@example.com',
            'password': 'DifferentPass123!',
            'display_name': 'Second User'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'already registered' in data['error'].lower()

    def test_user_registration_invalid_email(self, test_client):
        """Test registration fails with invalid email format."""
        response = test_client.post('/api/auth/register', json={
            'email': 'not-an-email',
            'password': 'ValidPassword123!',
            'display_name': 'Test User'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'email' in data['error'].lower()

    def test_user_registration_short_password(self, test_client):
        """Test registration fails with password < 8 characters."""
        response = test_client.post('/api/auth/register', json={
            'email': 'validuser@example.com',
            'password': 'Short1!',  # Only 7 characters
            'display_name': 'Test User'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert '8' in data['error']  # Error message mentions minimum length

    def test_user_login_success(self, test_client, db_session):
        """Test successful login with correct credentials."""
        # Register user first
        test_client.post('/api/auth/register', json={
            'email': 'logintest@example.com',
            'password': 'SecurePassword123!',
            'display_name': 'Login Test'
        })

        # Login with correct credentials
        response = test_client.post('/api/auth/login', json={
            'email': 'logintest@example.com',
            'password': 'SecurePassword123!'
        })

        assert response.status_code == 200
        data = response.get_json()

        # Verify response structure
        assert 'user' in data
        assert 'access_token' in data
        assert data['user']['email'] == 'logintest@example.com'
        assert data['user']['display_name'] == 'Login Test'
        assert 'last_login_at' in data['user']

        # Verify JWT token
        assert data['access_token'].count('.') == 2

        # Verify last_login_at was updated in database
        user = db_session.query(User).filter(User.email == 'logintest@example.com').first()
        assert user.last_login_at is not None

    def test_user_login_wrong_password(self, test_client):
        """Test login fails with incorrect password."""
        # Register user
        test_client.post('/api/auth/register', json={
            'email': 'passwordtest@example.com',
            'password': 'CorrectPassword123!',
            'display_name': 'Password Test'
        })

        # Login with wrong password
        response = test_client.post('/api/auth/login', json={
            'email': 'passwordtest@example.com',
            'password': 'WrongPassword123!'
        })

        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
        assert 'invalid credentials' in data['error'].lower()

    def test_user_login_nonexistent_user(self, test_client):
        """Test login fails with email that doesn't exist."""
        response = test_client.post('/api/auth/login', json={
            'email': 'nonexistent@example.com',
            'password': 'SomePassword123!'
        })

        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
        assert 'invalid credentials' in data['error'].lower()

    def test_protected_route_with_valid_token(self, test_client):
        """Test protected route access with valid JWT token."""
        # Register and login to get token
        register_response = test_client.post('/api/auth/register', json={
            'email': 'protected@example.com',
            'password': 'SecurePassword123!',
            'display_name': 'Protected Test'
        })
        token = register_response.get_json()['access_token']

        # Access protected endpoint with token
        response = test_client.get('/api/auth/me', headers={
            'Authorization': f'Bearer {token}'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['email'] == 'protected@example.com'
        assert data['display_name'] == 'Protected Test'
        assert 'id' in data
        assert 'created_at' in data

    def test_protected_route_without_token(self, test_client):
        """Test protected route fails without authorization header."""
        response = test_client.get('/api/auth/me')

        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
        assert 'authorization' in data['error'].lower()

    def test_protected_route_with_invalid_token(self, test_client):
        """Test protected route fails with invalid/malformed JWT token."""
        response = test_client.get('/api/auth/me', headers={
            'Authorization': 'Bearer invalid.jwt.token'
        })

        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
        assert 'invalid' in data['error'].lower() or 'expired' in data['error'].lower()
