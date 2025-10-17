"""
Unit tests for BcryptPasswordHasher.

These tests ensure the bcrypt password hashing implementation works correctly,
including hashing, verification, cost factors, edge cases, and interface compliance.
"""

import pytest
from domain.shared import PasswordHasher, PasswordHashingError
from infrastructure.security import BcryptPasswordHasher


class TestBcryptPasswordHasher:
    """Test basic password hashing and verification functionality."""

    def test_hash_password_returns_valid_hash(self):
        """Test that hashing returns a valid bcrypt hash."""
        hasher = BcryptPasswordHasher(cost_factor=10)
        password = "MySecurePassword123!"

        password_hash = hasher.hash(password)

        assert isinstance(password_hash, str)
        assert len(password_hash) == 60
        assert password_hash.startswith("$2b$")

    def test_verify_correct_password_returns_true(self):
        """Test that verification succeeds with correct password."""
        hasher = BcryptPasswordHasher(cost_factor=10)
        password = "MySecurePassword123!"

        password_hash = hasher.hash(password)
        is_valid = hasher.verify(password, password_hash)

        assert is_valid is True

    def test_verify_incorrect_password_returns_false(self):
        """Test that verification fails with incorrect password."""
        hasher = BcryptPasswordHasher(cost_factor=10)
        password = "MySecurePassword123!"
        wrong_password = "WrongPassword"

        password_hash = hasher.hash(password)
        is_valid = hasher.verify(wrong_password, password_hash)

        assert is_valid is False

    def test_implements_password_hasher_interface(self):
        """Test that BcryptPasswordHasher implements PasswordHasher interface."""
        hasher = BcryptPasswordHasher()

        assert isinstance(hasher, PasswordHasher)
        assert hasattr(hasher, 'hash')
        assert hasattr(hasher, 'verify')
        assert callable(hasher.hash)
        assert callable(hasher.verify)


class TestCostFactors:
    """Test different cost factors and their configuration."""

    def test_default_cost_factor_is_12(self):
        """Test that default cost factor is 12."""
        hasher = BcryptPasswordHasher()

        assert hasher.cost_factor == 12

    def test_custom_cost_factor(self):
        """Test creating hasher with custom cost factor."""
        hasher = BcryptPasswordHasher(cost_factor=10)

        assert hasher.cost_factor == 10

    def test_different_cost_factors_produce_valid_hashes(self):
        """Test that different cost factors all produce valid, verifiable hashes."""
        password = "TestPassword123"
        cost_factors = [10, 12, 14]

        for cost in cost_factors:
            hasher = BcryptPasswordHasher(cost_factor=cost)
            password_hash = hasher.hash(password)

            # Verify hash is valid
            assert password_hash.startswith("$2b$")
            assert hasher.verify(password, password_hash)

    def test_invalid_cost_factor_raises_error(self):
        """Test that invalid cost factors raise ValueError."""
        # Cost factor too low
        with pytest.raises(ValueError, match="Cost factor must be between 4 and 31"):
            BcryptPasswordHasher(cost_factor=3)

        # Cost factor too high
        with pytest.raises(ValueError, match="Cost factor must be between 4 and 31"):
            BcryptPasswordHasher(cost_factor=50)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_password_raises_error(self):
        """Test that empty password raises ValueError."""
        hasher = BcryptPasswordHasher(cost_factor=10)

        with pytest.raises(ValueError, match="Password cannot be empty"):
            hasher.hash("")

    def test_empty_password_verification_raises_error(self):
        """Test that verifying with empty password raises ValueError."""
        hasher = BcryptPasswordHasher(cost_factor=10)
        password_hash = hasher.hash("ValidPassword123")

        with pytest.raises(ValueError, match="Password cannot be empty"):
            hasher.verify("", password_hash)

    def test_empty_hash_verification_raises_error(self):
        """Test that verifying with empty hash raises ValueError."""
        hasher = BcryptPasswordHasher(cost_factor=10)

        with pytest.raises(ValueError, match="Password hash cannot be empty"):
            hasher.verify("password", "")

    def test_long_password_within_limit(self):
        """Test password at bcrypt's 72-byte limit works."""
        hasher = BcryptPasswordHasher(cost_factor=10)
        # 70 characters is safely within the 72-byte limit
        long_password = "a" * 70

        password_hash = hasher.hash(long_password)

        assert hasher.verify(long_password, password_hash)

    def test_password_exceeding_72_byte_limit_raises_error(self):
        """Test that password exceeding bcrypt's 72-byte limit raises error."""
        hasher = BcryptPasswordHasher(cost_factor=10)
        # 100 characters exceeds the 72-byte limit
        too_long_password = "a" * 100

        with pytest.raises(PasswordHashingError):
            hasher.hash(too_long_password)

    def test_special_characters_in_password(self):
        """Test password with special characters."""
        hasher = BcryptPasswordHasher(cost_factor=10)
        special_password = "P@ssw0rd!#$%^&*()_+-=[]{}|;':\",./<>?"

        password_hash = hasher.hash(special_password)

        assert hasher.verify(special_password, password_hash)

    def test_unicode_characters_in_password(self):
        """Test password with unicode characters."""
        hasher = BcryptPasswordHasher(cost_factor=10)
        unicode_password = "パスワード123🔒"

        password_hash = hasher.hash(unicode_password)

        assert hasher.verify(unicode_password, password_hash)

    def test_invalid_hash_format_returns_false(self):
        """Test that invalid hash format returns False instead of raising."""
        hasher = BcryptPasswordHasher(cost_factor=10)

        # Invalid hash should return False, not raise exception
        is_valid = hasher.verify("password", "not_a_valid_bcrypt_hash")

        assert is_valid is False

    def test_corrupted_hash_returns_false(self):
        """Test that corrupted hash returns False."""
        hasher = BcryptPasswordHasher(cost_factor=10)
        password = "TestPassword123"
        password_hash = hasher.hash(password)

        # Corrupt the hash
        corrupted_hash = password_hash[:-5] + "xxxxx"

        is_valid = hasher.verify(password, corrupted_hash)

        assert is_valid is False


class TestUniqueSalts:
    """Test that salt generation produces unique hashes."""

    def test_same_password_produces_different_hashes(self):
        """Test that hashing the same password multiple times produces different hashes."""
        hasher = BcryptPasswordHasher(cost_factor=10)
        password = "SamePassword123"

        # Hash the same password 5 times
        hashes = [hasher.hash(password) for _ in range(5)]

        # All hashes should be unique (due to random salt)
        unique_hashes = set(hashes)
        assert len(unique_hashes) == 5

    def test_all_salted_hashes_verify_correctly(self):
        """Test that all uniquely salted hashes verify the same password."""
        hasher = BcryptPasswordHasher(cost_factor=10)
        password = "TestPassword123"

        # Generate multiple hashes
        hashes = [hasher.hash(password) for _ in range(5)]

        # All hashes should verify the original password
        for password_hash in hashes:
            assert hasher.verify(password, password_hash)


class TestPasswordHasherErrorHandling:
    """Test error handling and exception wrapping."""

    def test_hashing_error_wraps_exception(self):
        """Test that hashing errors are wrapped in PasswordHashingError."""
        hasher = BcryptPasswordHasher(cost_factor=10)

        # Trigger an error by exceeding byte limit
        with pytest.raises(PasswordHashingError) as exc_info:
            hasher.hash("a" * 100)

        # Verify the error message and original error
        assert "Failed to hash password" in str(exc_info.value)
        assert exc_info.value.original_error is not None


@pytest.fixture
def password_hasher():
    """Fixture providing a BcryptPasswordHasher instance for testing."""
    return BcryptPasswordHasher(cost_factor=10)


@pytest.fixture
def test_password():
    """Fixture providing a test password string."""
    return "TestPassword123!"
