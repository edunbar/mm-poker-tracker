"""
Bcrypt implementation of the PasswordHasher interface.

This module provides a concrete implementation of password hashing using
the bcrypt algorithm, which is designed specifically for password hashing
and includes automatic salting.
"""

import bcrypt
from domain.shared.password_hasher import PasswordHasher, PasswordHashingError


class BcryptPasswordHasher(PasswordHasher):
    """
    Bcrypt-based implementation of PasswordHasher.

    Bcrypt is a password hashing function designed by Niels Provos and David Mazières,
    based on the Blowfish cipher. It incorporates a salt to protect against rainbow
    table attacks and is adaptive, allowing the cost factor to be increased as
    computers become more powerful.

    Features:
    - Automatic salt generation
    - Configurable cost factor (work factor)
    - Resistant to rainbow table and brute-force attacks
    - Time-tested and widely adopted

    Example:
        >>> hasher = BcryptPasswordHasher(cost_factor=12)
        >>> password_hash = hasher.hash("my_secure_password")
        >>> is_valid = hasher.verify("my_secure_password", password_hash)
        >>> print(is_valid)  # True
    """

    def __init__(self, cost_factor: int = 12) -> None:
        """
        Initialize the bcrypt password hasher.

        Args:
            cost_factor: The bcrypt cost factor (work factor), between 4 and 31.
                        Higher values are more secure but slower. Default is 12.
                        Each increment doubles the computation time.
                        Recommended values:
                        - 12: Good balance for most applications (~300ms)
                        - 14: Higher security for sensitive applications (~1s)
                        - 10: Faster for high-throughput scenarios (~80ms)

        Raises:
            ValueError: If cost_factor is not between 4 and 31

        Note:
            The cost factor determines how many iterations the hashing algorithm
            performs. The actual number of iterations is 2^cost_factor.
        """
        if not 4 <= cost_factor <= 31:
            raise ValueError("Cost factor must be between 4 and 31")
        self.cost_factor = cost_factor

    def hash(self, password: str) -> str:
        """
        Hash a plaintext password using bcrypt.

        The resulting hash includes the salt and cost factor, so it can be
        verified later without storing these separately.

        Args:
            password: The plaintext password to hash

        Returns:
            The bcrypt hash as a UTF-8 string, suitable for storage in VARCHAR(255)

        Raises:
            ValueError: If password is empty or None
            PasswordHashingError: If the bcrypt hashing operation fails

        Note:
            Bcrypt hashes are always 60 characters long and start with "$2b$"
            followed by the cost factor.
        """
        if not password:
            raise ValueError("Password cannot be empty")

        try:
            # Convert password to bytes (bcrypt requires bytes)
            password_bytes = password.encode('utf-8')

            # Generate salt and hash the password
            salt = bcrypt.gensalt(rounds=self.cost_factor)
            hashed_bytes = bcrypt.hashpw(password_bytes, salt)

            # Convert hash back to string for storage
            return hashed_bytes.decode('utf-8')

        except Exception as e:
            raise PasswordHashingError(
                f"Failed to hash password: {str(e)}",
                original_error=e
            )

    def verify(self, password: str, password_hash: str) -> bool:
        """
        Verify a plaintext password against a bcrypt hash.

        This method is constant-time to prevent timing attacks.

        Args:
            password: The plaintext password to verify
            password_hash: The stored bcrypt hash to check against

        Returns:
            True if the password matches the hash, False otherwise

        Raises:
            ValueError: If password or password_hash is empty or None
            PasswordHashingError: If the verification operation fails

        Note:
            This method will return False for invalid hashes rather than
            raising an exception, unless there's a system-level error.
        """
        if not password:
            raise ValueError("Password cannot be empty")
        if not password_hash:
            raise ValueError("Password hash cannot be empty")

        try:
            # Convert strings to bytes
            password_bytes = password.encode('utf-8')
            hash_bytes = password_hash.encode('utf-8')

            # Verify password (constant-time comparison)
            return bcrypt.checkpw(password_bytes, hash_bytes)

        except ValueError as e:
            # Invalid hash format - return False rather than raising
            # This can happen if the stored hash is corrupted
            return False

        except Exception as e:
            raise PasswordHashingError(
                f"Failed to verify password: {str(e)}",
                original_error=e
            )
