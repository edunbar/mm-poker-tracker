"""
UserId value object for the identity domain.

This module provides a validated user identifier value object
that wraps UUID values with type safety.
"""

from __future__ import annotations
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class UserId:
    """
    User identifier value object.

    Wraps a UUID string with validation to ensure type safety and
    provide a domain-specific identifier type.

    Attributes:
        value: The UUID string

    Example:
        >>> from uuid import uuid4
        >>> user_id = UserId(str(uuid4()))
        >>> print(str(user_id))  # "123e4567-e89b-12d3-a456-426614174000"

    Raises:
        ValueError: If value is invalid (empty or not a valid UUID format)
    """

    value: str

    def __post_init__(self) -> None:
        """
        Validate that the value is a valid UUID.

        Raises:
            ValueError: If value is empty or not a valid UUID format
        """
        if not self.value:
            raise ValueError("UserId cannot be empty")

        if not isinstance(self.value, str):
            raise ValueError("UserId must be a string")

        # Strip whitespace
        cleaned_value = self.value.strip()
        if not cleaned_value:
            raise ValueError("UserId cannot be empty or whitespace")

        # Update value with cleaned version
        object.__setattr__(self, 'value', cleaned_value)

        # Validate UUID format
        try:
            UUID(self.value)
        except (ValueError, AttributeError) as e:
            raise ValueError(
                f"Invalid UUID format: {self.value}. "
                "Must be a valid UUID string."
            ) from e

    def __str__(self) -> str:
        """String representation returns the UUID value."""
        return self.value

    def __hash__(self) -> int:
        """Hash based on UUID value for use in sets/dicts."""
        return hash(self.value)

    @classmethod
    def from_uuid(cls, uuid_obj: UUID) -> UserId:
        """
        Create a UserId from a UUID object.

        Args:
            uuid_obj: A UUID object

        Returns:
            UserId wrapping the UUID string

        Example:
            >>> from uuid import uuid4
            >>> uuid_obj = uuid4()
            >>> user_id = UserId.from_uuid(uuid_obj)
        """
        return cls(str(uuid_obj))
