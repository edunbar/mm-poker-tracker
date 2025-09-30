"""
Value objects for the poker domain.

Value objects are immutable objects that are defined by their value rather than identity.
They encapsulate data and enforce invariants, ensuring type safety and business rules.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Self
from dataclasses import dataclass
from uuid import UUID, uuid4


class Money:
    """
    Money value object for precise financial calculations.

    Uses Decimal internally to avoid floating-point precision issues
    that could cause financial discrepancies.
    """

    def __init__(self, amount: str | int | float | Decimal) -> None:
        """
        Initialize Money with precise decimal representation.

        Args:
            amount: The monetary amount

        Raises:
            ValueError: If amount is not a valid monetary value
        """
        try:
            self._amount = Decimal(str(amount)).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        except Exception as e:
            raise ValueError(f"Invalid monetary amount: {amount}") from e

        # Allow negative amounts for business cases like debt/balances
        # if self._amount < 0:
        #     raise ValueError("Money amount cannot be negative")

    @classmethod
    def zero(cls) -> Self:
        """Create a zero money amount."""
        return cls(0)

    @property
    def amount(self) -> Decimal:
        """Get the decimal amount."""
        return self._amount

    def __add__(self, other: Money) -> Money:
        """Add two money amounts."""
        if not isinstance(other, Money):
            raise TypeError("Can only add Money to Money")
        return Money(self._amount + other._amount)

    def __sub__(self, other: Money) -> Money:
        """Subtract money amounts."""
        if not isinstance(other, Money):
            raise TypeError("Can only subtract Money from Money")
        result_amount = self._amount - other._amount
        # Allow negative results for business cases like debt/balances
        return Money(result_amount)

    def __mul__(self, multiplier: int | float | Decimal) -> Money:
        """Multiply money by a scalar."""
        return Money(self._amount * Decimal(str(multiplier)))

    def __truediv__(self, divisor: int | float | Decimal) -> Money:
        """Divide money by a scalar."""
        if divisor == 0:
            raise ValueError("Cannot divide by zero")
        return Money(self._amount / Decimal(str(divisor)))

    def __eq__(self, other: object) -> bool:
        """Check equality with another Money instance."""
        if not isinstance(other, Money):
            return False
        return self._amount == other._amount

    def __lt__(self, other: Money) -> bool:
        """Check if this amount is less than another."""
        if not isinstance(other, Money):
            raise TypeError("Can only compare Money with Money")
        return self._amount < other._amount

    def __le__(self, other: Money) -> bool:
        """Check if this amount is less than or equal to another."""
        if not isinstance(other, Money):
            raise TypeError("Can only compare Money with Money")
        return self._amount <= other._amount

    def __gt__(self, other: Money) -> bool:
        """Check if this amount is greater than another."""
        if not isinstance(other, Money):
            raise TypeError("Can only compare Money with Money")
        return self._amount > other._amount

    def __ge__(self, other: Money) -> bool:
        """Check if this amount is greater than or equal to another."""
        if not isinstance(other, Money):
            raise TypeError("Can only compare Money with Money")
        return self._amount >= other._amount

    def __hash__(self) -> int:
        """Make Money hashable for use in sets and as dict keys."""
        return hash(self._amount)

    def __str__(self) -> str:
        """String representation for display."""
        return f"${self._amount}"

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"Money({self._amount})"

    def to_float(self) -> float:
        """
        Convert to float for legacy compatibility.

        Warning: Use with caution as this can introduce floating-point precision issues.
        """
        return float(self._amount)

    def is_positive(self) -> bool:
        """Check if the amount is positive."""
        return self._amount > 0

    def is_zero(self) -> bool:
        """Check if the amount is zero."""
        return self._amount == 0

    def is_non_negative(self) -> bool:
        """Check if the amount is zero or positive."""
        return self._amount >= 0


@dataclass(frozen=True)
class SessionId:
    """Type-safe wrapper for session identifiers."""

    value: str

    def __post_init__(self) -> None:
        """Validate session ID format."""
        if not self.value:
            raise ValueError("Session ID cannot be empty")

        # Validate UUID format
        try:
            UUID(self.value)
        except ValueError as e:
            raise ValueError(f"Session ID must be a valid UUID: {self.value}") from e

    @classmethod
    def generate(cls) -> Self:
        """Generate a new session ID."""
        return cls(str(uuid4()))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PlayerId:
    """Type-safe wrapper for player identifiers."""

    value: str

    def __post_init__(self) -> None:
        """Validate player ID format."""
        if not self.value:
            raise ValueError("Player ID cannot be empty")

        # Validate UUID format
        try:
            UUID(self.value)
        except ValueError as e:
            raise ValueError(f"Player ID must be a valid UUID: {self.value}") from e

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class GameId:
    """Type-safe wrapper for game identifiers."""

    value: str

    def __post_init__(self) -> None:
        """Validate game ID format."""
        if not self.value:
            raise ValueError("Game ID cannot be empty")

        # GameId can be either a UUID (36 chars) or a public code (5 chars)
        # This allows it to represent both database IDs and public codes
        if len(self.value) not in [5, 36]:
            raise ValueError("Game ID must be either 5 characters (public code) or 36 characters (UUID)")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Hand:
    """
    Represents a single poker hand with its financial result for a specific player.
    """

    hand_number: int
    pot_size: Money
    player_result: Money  # Positive for winnings, zero for break-even

    def __post_init__(self) -> None:
        """Validate hand data."""
        if self.hand_number <= 0:
            raise ValueError("Hand number must be positive")

        if not isinstance(self.pot_size, Money):
            raise TypeError("pot_size must be a Money instance")

        if not isinstance(self.player_result, Money):
            raise TypeError("player_result must be a Money instance")

    def is_winning_hand(self) -> bool:
        """Check if this was a winning hand for the player."""
        return self.player_result.is_positive()

    def is_break_even_hand(self) -> bool:
        """Check if this was a break-even hand for the player."""
        return self.player_result.is_zero()


@dataclass(frozen=True)
class SessionDuration:
    """Represents the duration of a poker session in minutes."""

    minutes: int

    def __post_init__(self) -> None:
        """Validate duration."""
        if self.minutes < 0:
            raise ValueError("Session duration cannot be negative")

    @classmethod
    def from_hours(cls, hours: float) -> Self:
        """Create duration from hours."""
        if hours < 0:
            raise ValueError("Hours cannot be negative")
        return cls(int(hours * 60))

    def to_hours(self) -> float:
        """Convert duration to hours."""
        return self.minutes / 60.0

    def is_marathon_session(self) -> bool:
        """Check if this is a marathon session (over 12 hours)."""
        return self.minutes > 12 * 60

    def __str__(self) -> str:
        hours = self.minutes // 60
        mins = self.minutes % 60
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"


@dataclass(frozen=True)
class SessionStats:
    """Aggregated statistics for a poker session."""

    total_hands: int
    winning_hands: int
    break_even_hands: int
    total_pot_value: Money

    def __post_init__(self) -> None:
        """Validate statistics."""
        if self.total_hands < 0:
            raise ValueError("Total hands cannot be negative")
        if self.winning_hands < 0:
            raise ValueError("Winning hands cannot be negative")
        if self.break_even_hands < 0:
            raise ValueError("Break-even hands cannot be negative")
        if self.winning_hands + self.break_even_hands > self.total_hands:
            raise ValueError("Winning + break-even hands cannot exceed total hands")

    @property
    def losing_hands(self) -> int:
        """Calculate number of losing hands."""
        return self.total_hands - self.winning_hands - self.break_even_hands

    def win_rate(self) -> float:
        """Calculate win rate as a percentage."""
        if self.total_hands == 0:
            return 0.0
        return (self.winning_hands / self.total_hands) * 100

    def break_even_rate(self) -> float:
        """Calculate break-even rate as a percentage."""
        if self.total_hands == 0:
            return 0.0
        return (self.break_even_hands / self.total_hands) * 100


@dataclass(frozen=True)
class PublicCode:
    """
    Public game code for sharing and identifying games.

    A short, case-insensitive alphanumeric code that players use to access games.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate public code format."""
        if not isinstance(self.value, str):
            raise TypeError("Public code must be a string")

        # Normalize to uppercase
        object.__setattr__(self, 'value', self.value.upper().strip())

        if not self.value:
            raise ValueError("Public code cannot be empty")

        if len(self.value) < 3 or len(self.value) > 10:
            raise ValueError("Public code must be between 3 and 10 characters")

        # Only allow alphanumeric characters
        if not self.value.isalnum():
            raise ValueError("Public code must contain only letters and numbers")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class AdminToken:
    """
    Secure administrative token for game management.

    A long, cryptographically secure token used for administrative operations.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate admin token format."""
        if not isinstance(self.value, str):
            raise TypeError("Admin token must be a string")

        if not self.value.strip():
            raise ValueError("Admin token cannot be empty")

        # Admin tokens should be at least 32 characters for security
        if len(self.value) < 32:
            raise ValueError("Admin token must be at least 32 characters long")

        # Ensure it's URL-safe (basic check)
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        if not all(c in allowed_chars for c in self.value):
            raise ValueError("Admin token contains invalid characters")

    def __str__(self) -> str:
        # Never expose the full token in string representation for security
        return f"AdminToken({self.value[:8]}...)"

    def masked_value(self) -> str:
        """Return a masked version for logging/display."""
        if len(self.value) <= 8:
            return "****"
        return f"{self.value[:4]}...{self.value[-4:]}"


@dataclass(frozen=True)
class GameTitle:
    """
    Optional title/name for a game.

    A human-readable name to help identify and organize games.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate game title."""
        if not isinstance(self.value, str):
            raise TypeError("Game title must be a string")

        # Normalize whitespace
        normalized = ' '.join(self.value.split())
        object.__setattr__(self, 'value', normalized)

        if not self.value:
            raise ValueError("Game title cannot be empty or only whitespace")

        if len(self.value) > 100:
            raise ValueError("Game title must be 100 characters or less")

    def __str__(self) -> str:
        return self.value