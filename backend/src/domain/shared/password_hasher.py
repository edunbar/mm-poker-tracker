"""
Password hashing interface for the domain layer.

This module defines the abstract interface for password hashing operations,
allowing the domain layer to remain independent of specific hashing implementations
(bcrypt, argon2, scrypt, etc.).
"""

from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    """
    Abstract interface for password hashing operations.

    This interface defines the contract for secure password hashing without
    specifying the actual implementation algorithm. This allows the domain
    layer to work with passwords securely while remaining independent of
    infrastructure concerns.

    Implementations should:
    - Use a cryptographically secure hashing algorithm (bcrypt, argon2, etc.)
    - Include proper salting automatically
    - Use appropriate cost/iteration factors
    - Handle encoding/decoding transparently
    """

    @abstractmethod
    def hash(self, password: str) -> str:
        """
        Hash a plaintext password securely.

        Args:
            password: The plaintext password to hash

        Returns:
            The hashed password as a string suitable for database storage

        Raises:
            PasswordHashingError: If the hashing operation fails
            ValueError: If the password is empty or invalid
        """
        pass

    @abstractmethod
    def verify(self, password: str, password_hash: str) -> bool:
        """
        Verify a plaintext password against a hash.

        Args:
            password: The plaintext password to verify
            password_hash: The stored password hash to check against

        Returns:
            True if the password matches the hash, False otherwise

        Raises:
            PasswordHashingError: If the verification operation fails
            ValueError: If password or hash is empty or invalid
        """
        pass


class PasswordHashingError(Exception):
    """
    Base exception for password hashing operations.

    This allows the domain layer to handle hashing errors
    without coupling to specific hashing library exceptions.
    """

    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        """
        Initialize the exception.

        Args:
            message: Human-readable error message
            original_error: The original exception that caused this error (optional)
        """
        super().__init__(message)
        self.message = message
        self.original_error = original_error
