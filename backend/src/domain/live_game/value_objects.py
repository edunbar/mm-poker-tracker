"""
Value objects for live game domain.

This module defines immutable value objects used throughout the live game domain,
including identifiers and the JoinCode value object with validation.
"""

from dataclasses import dataclass
from typing import NewType

# Type aliases for domain identifiers (UUIDs as strings)
LiveGameId = NewType('LiveGameId', str)
ParticipantId = NewType('ParticipantId', str)
TransactionId = NewType('TransactionId', str)


@dataclass(frozen=True)
class JoinCode:
    """
    4-character alphanumeric join code for live games.

    Join codes are used to allow users to easily join active live games
    without needing to share long UUIDs. The code excludes confusing
    characters (O, I, 0, 1, L) to prevent user input errors.

    Attributes:
        value: The 4-character join code string

    Raises:
        ValueError: If code is not exactly 4 characters, not alphanumeric,
                   or not uppercase

    Example:
        >>> code = JoinCode("A3X7")
        >>> print(code.value)
        A3X7
    """
    value: str

    def __post_init__(self):
        """Validate join code format."""
        if len(self.value) != 4:
            raise ValueError("Join code must be exactly 4 characters")
        if not self.value.isalnum():
            raise ValueError("Join code must be alphanumeric")
        if not self.value.isupper():
            raise ValueError("Join code must be uppercase")

    def __str__(self) -> str:
        """Return string representation of join code."""
        return self.value
