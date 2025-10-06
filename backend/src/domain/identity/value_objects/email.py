"""
Email value object for the identity domain.

This module provides a validated email value object that enforces
email format rules and length constraints.
"""

from __future__ import annotations
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Email:
    """
    Email address value object with validation.

    Ensures emails are properly formatted and within length constraints.
    Provides normalization (lowercase) for consistent storage and comparison.

    Attributes:
        value: The email address string

    Example:
        >>> email = Email("user@example.com")
        >>> print(email.normalized())  # "user@example.com"
        >>> print(str(email))  # "user@example.com"

    Raises:
        ValueError: If email is invalid (empty, too long, or malformed)
    """

    value: str

    # Email regex pattern (RFC 5322 simplified)
    # Matches most common email formats while rejecting obvious invalids
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    # Maximum email length (standard database VARCHAR limit)
    MAX_LENGTH = 255

    def __post_init__(self) -> None:
        """
        Validate email format and constraints.

        Raises:
            ValueError: If email is empty, too long, or doesn't match pattern
        """
        if not self.value:
            raise ValueError("Email cannot be empty")

        if not isinstance(self.value, str):
            raise ValueError("Email must be a string")

        # Strip whitespace
        cleaned_email = self.value.strip()
        if not cleaned_email:
            raise ValueError("Email cannot be empty or whitespace")

        # Update value with cleaned version
        object.__setattr__(self, 'value', cleaned_email)

        # Check length
        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(
                f"Email cannot exceed {self.MAX_LENGTH} characters "
                f"(got {len(self.value)})"
            )

        # Validate format using regex
        if not self.EMAIL_PATTERN.match(self.value):
            raise ValueError(
                f"Invalid email format: {self.value}. "
                "Email must be in format: user@domain.com"
            )

    def normalized(self) -> str:
        """
        Get the normalized (lowercase) email address.

        Email addresses are case-insensitive per RFC 5321, so normalization
        ensures consistent storage and comparison.

        Returns:
            Lowercase version of the email address

        Example:
            >>> email = Email("User@Example.COM")
            >>> email.normalized()  # "user@example.com"
        """
        return self.value.lower()

    def __str__(self) -> str:
        """String representation returns the email value."""
        return self.value

    def __hash__(self) -> int:
        """Hash based on normalized email for use in sets/dicts."""
        return hash(self.normalized())

    def __eq__(self, other: object) -> bool:
        """
        Compare emails case-insensitively.

        Args:
            other: Another Email object to compare

        Returns:
            True if emails match (case-insensitive), False otherwise
        """
        if not isinstance(other, Email):
            return False
        return self.normalized() == other.normalized()
