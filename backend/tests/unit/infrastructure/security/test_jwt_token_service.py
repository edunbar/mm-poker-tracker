"""
Unit tests for JWTTokenService.

These tests ensure JWT token generation and validation work correctly,
including expiration handling, invalid token handling, and edge cases.
"""

import pytest
import jwt
from datetime import datetime, timedelta, timezone
from freezegun import freeze_time
from infrastructure.security.jwt_token_service import JWTTokenService


class TestJWTTokenServiceInitialization:
    """Test JWTTokenService initialization and configuration."""

    def test_initialization_with_secret_key(self):
        """Test creating service with explicit secret key."""
        service = JWTTokenService(secret_key="test_secret_key_123")

        assert service.secret_key == "test_secret_key_123"
        assert service.token_expiry_days == 7
        assert service.algorithm == 'HS256'

    def test_initialization_with_custom_expiry(self):
        """Test creating service with custom expiry days."""
        service = JWTTokenService(secret_key="test_secret", token_expiry_days=14)

        assert service.token_expiry_days == 14

    def test_initialization_without_secret_raises_error(self, monkeypatch):
        """Test that missing secret key raises ValueError."""
        # Remove JWT_SECRET from environment
        monkeypatch.delenv('JWT_SECRET', raising=False)

        with pytest.raises(ValueError, match="JWT secret key not provided"):
            JWTTokenService()

    def test_initialization_from_environment(self, monkeypatch):
        """Test that secret key is read from JWT_SECRET environment variable."""
        monkeypatch.setenv('JWT_SECRET', 'env_secret_key_456')

        service = JWTTokenService()

        assert service.secret_key == 'env_secret_key_456'

    def test_invalid_expiry_days_raises_error(self):
        """Test that invalid expiry days raise ValueError."""
        with pytest.raises(ValueError, match="token_expiry_days must be at least 1"):
            JWTTokenService(secret_key="test_secret", token_expiry_days=0)

        with pytest.raises(ValueError, match="token_expiry_days must be at least 1"):
            JWTTokenService(secret_key="test_secret", token_expiry_days=-1)


class TestGenerateAccessToken:
    """Test JWT access token generation."""

    def test_generate_token_returns_string(self, jwt_service):
        """Test that token generation returns a string."""
        token = jwt_service.generate_access_token("user_123", "user@example.com")

        assert isinstance(token, str)
        assert len(token) > 0

    def test_generated_token_contains_correct_payload(self, jwt_service):
        """Test that generated token contains expected payload fields."""
        user_id = "user_123"
        email = "user@example.com"

        token = jwt_service.generate_access_token(user_id, email)

        # Decode without verification to check payload
        payload = jwt.decode(token, options={"verify_signature": False})

        assert payload['user_id'] == user_id
        assert payload['email'] == email
        assert 'iat' in payload
        assert 'exp' in payload

    @freeze_time("2025-01-01 12:00:00")
    def test_token_expiry_is_correct(self, jwt_service):
        """Test that token expiry is set correctly (7 days from now)."""
        token = jwt_service.generate_access_token("user_123", "user@example.com")

        payload = jwt.decode(token, options={"verify_signature": False})

        # Calculate expected expiry
        now = datetime.now(timezone.utc)
        expected_exp = now + timedelta(days=7)

        # Convert timestamps to datetime for comparison
        actual_exp = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)

        assert abs((actual_exp - expected_exp).total_seconds()) < 2

    def test_empty_user_id_raises_error(self, jwt_service):
        """Test that empty user_id raises ValueError."""
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            jwt_service.generate_access_token("", "user@example.com")

    def test_empty_email_raises_error(self, jwt_service):
        """Test that empty email raises ValueError."""
        with pytest.raises(ValueError, match="email cannot be empty"):
            jwt_service.generate_access_token("user_123", "")

    def test_different_users_generate_different_tokens(self, jwt_service):
        """Test that different users get different tokens."""
        token1 = jwt_service.generate_access_token("user_1", "user1@example.com")
        token2 = jwt_service.generate_access_token("user_2", "user2@example.com")

        assert token1 != token2


class TestDecodeToken:
    """Test JWT token decoding and validation."""

    def test_decode_valid_token_returns_payload(self, jwt_service, sample_user_data):
        """Test that decoding a valid token returns the payload."""
        user_id, email = sample_user_data
        token = jwt_service.generate_access_token(user_id, email)

        payload = jwt_service.decode_token(token)

        assert payload is not None
        assert payload['user_id'] == user_id
        assert payload['email'] == email

    def test_decode_expired_token_returns_none(self, jwt_service, sample_user_data):
        """Test that expired token returns None."""
        user_id, email = sample_user_data

        # Create a token that expires in 1 second
        short_lived_service = JWTTokenService(
            secret_key="test_secret",
            token_expiry_days=1
        )

        # Freeze time and generate token
        with freeze_time("2025-01-01 12:00:00") as frozen_time:
            token = short_lived_service.generate_access_token(user_id, email)

            # Advance time by 2 days (past expiry)
            frozen_time.move_to("2025-01-03 12:00:00")

            payload = short_lived_service.decode_token(token)

        assert payload is None

    def test_decode_invalid_signature_returns_none(self, jwt_service, sample_user_data):
        """Test that token with invalid signature returns None."""
        user_id, email = sample_user_data
        token = jwt_service.generate_access_token(user_id, email)

        # Create different service with different secret
        other_service = JWTTokenService(secret_key="different_secret")

        payload = other_service.decode_token(token)

        assert payload is None

    def test_decode_malformed_token_returns_none(self, jwt_service):
        """Test that malformed token returns None."""
        malformed_tokens = [
            "not.a.jwt.token",
            "invalid_token",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid",
            "header.payload.signature",
        ]

        for token in malformed_tokens:
            payload = jwt_service.decode_token(token)
            assert payload is None

    def test_decode_empty_token_returns_none(self, jwt_service):
        """Test that empty token returns None."""
        payload = jwt_service.decode_token("")

        assert payload is None

    def test_decode_none_token_returns_none(self, jwt_service):
        """Test that None token returns None."""
        payload = jwt_service.decode_token(None)

        assert payload is None


class TestTokenRoundTrip:
    """Test full token lifecycle: generate → decode."""

    def test_token_round_trip_preserves_data(self, jwt_service):
        """Test that generating and decoding preserves user data."""
        user_id = "user_uuid_123"
        email = "test@example.com"

        # Generate token
        token = jwt_service.generate_access_token(user_id, email)

        # Decode token
        payload = jwt_service.decode_token(token)

        assert payload['user_id'] == user_id
        assert payload['email'] == email

    def test_multiple_tokens_decode_independently(self, jwt_service):
        """Test that multiple tokens can be decoded independently."""
        # Generate multiple tokens
        token1 = jwt_service.generate_access_token("user_1", "user1@example.com")
        token2 = jwt_service.generate_access_token("user_2", "user2@example.com")
        token3 = jwt_service.generate_access_token("user_3", "user3@example.com")

        # Decode all tokens
        payload1 = jwt_service.decode_token(token1)
        payload2 = jwt_service.decode_token(token2)
        payload3 = jwt_service.decode_token(token3)

        # Verify each payload has correct data
        assert payload1['user_id'] == "user_1"
        assert payload2['user_id'] == "user_2"
        assert payload3['user_id'] == "user_3"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_token_with_special_characters_in_email(self, jwt_service):
        """Test token generation with special characters in email."""
        emails = [
            "user+tag@example.com",
            "user.name@example.co.uk",
            "user_123@test-domain.com",
        ]

        for email in emails:
            token = jwt_service.generate_access_token("user_123", email)
            payload = jwt_service.decode_token(token)

            assert payload is not None
            assert payload['email'] == email

    def test_token_with_uuid_user_id(self, jwt_service):
        """Test token generation with UUID string."""
        from uuid import uuid4

        user_id = str(uuid4())
        email = "user@example.com"

        token = jwt_service.generate_access_token(user_id, email)
        payload = jwt_service.decode_token(token)

        assert payload is not None
        assert payload['user_id'] == user_id

    def test_decode_token_with_extra_whitespace(self, jwt_service, sample_user_data):
        """Test decoding token with leading/trailing whitespace."""
        user_id, email = sample_user_data
        token = jwt_service.generate_access_token(user_id, email)

        # Add whitespace
        token_with_whitespace = "  " + token + "  "

        # Should fail with whitespace (JWT spec doesn't allow it)
        payload = jwt_service.decode_token(token_with_whitespace)

        assert payload is None


# Fixtures

@pytest.fixture
def jwt_service():
    """Fixture providing a JWTTokenService instance for testing."""
    return JWTTokenService(secret_key="test_secret_key_for_testing_12345")


@pytest.fixture
def sample_user_data():
    """Fixture providing sample user ID and email."""
    return ("user_uuid_123", "testuser@example.com")
