"""
Value objects for the player domain.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from decimal import Decimal


@dataclass(frozen=True)
class PlayerId:
    """Unique player identifier."""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("PlayerId must be a non-empty string")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ExternalId:
    """External identifier for a verified player (e.g., Venmo, real name)."""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("ExternalId must be a non-empty string")
        # Strip whitespace
        object.__setattr__(self, 'value', self.value.strip())

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PlayerName:
    """Player display name or session name."""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("PlayerName must be a non-empty string")
        # Strip whitespace
        object.__setattr__(self, 'value', self.value.strip())

    def normalized(self) -> str:
        """Return lowercase normalized version for comparison."""
        return self.value.lower().strip()

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class MatchScore:
    """Similarity score for player matching (0-100)."""
    value: int

    def __post_init__(self):
        if not isinstance(self.value, int):
            raise ValueError("MatchScore must be an integer")
        if self.value < 0 or self.value > 100:
            raise ValueError("MatchScore must be between 0 and 100")

    def is_strong_match(self) -> bool:
        """Returns True if score indicates a strong match (>= 80)."""
        return self.value >= 80

    def is_moderate_match(self) -> bool:
        """Returns True if score indicates a moderate match (50-79)."""
        return 50 <= self.value < 80

    def is_weak_match(self) -> bool:
        """Returns True if score indicates a weak match (30-49)."""
        return 30 <= self.value < 50

    def __int__(self) -> int:
        return self.value


@dataclass(frozen=True)
class MatchReason:
    """Reason for a player match."""
    description: str
    score_contribution: int

    def __post_init__(self):
        if not self.description:
            raise ValueError("MatchReason description cannot be empty")
        if self.score_contribution < 0:
            raise ValueError("MatchReason score_contribution must be non-negative")


@dataclass(frozen=True)
class SessionStats:
    """Statistics for a player's session."""
    buy_in: int  # in cents
    cash_out: int  # in cents
    net: int  # in cents
    in_game: int  # in cents

    def __post_init__(self):
        # Validate all values are integers
        if not all(isinstance(v, int) for v in [self.buy_in, self.cash_out, self.net, self.in_game]):
            raise ValueError("All SessionStats values must be integers (cents)")

    def to_dollars(self) -> dict:
        """Convert cents to dollars for display."""
        return {
            'buy_in': Decimal(self.buy_in) / 100,
            'cash_out': Decimal(self.cash_out) / 100,
            'net': Decimal(self.net) / 100,
            'in_game': Decimal(self.in_game) / 100
        }