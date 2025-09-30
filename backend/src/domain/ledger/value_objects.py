"""
Value objects for the ledger domain.

These value objects encapsulate data and enforce business rules for ledger operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List
from uuid import UUID


@dataclass(frozen=True)
class LedgerEntryId:
    """
    Unique identifier for a ledger entry (SessionPlayerSummary).

    Composed of session_id + player_id since this is the natural key.
    """

    session_id: str
    player_id: str

    def __post_init__(self) -> None:
        """Validate ledger entry ID components."""
        if not isinstance(self.session_id, str) or not self.session_id.strip():
            raise ValueError("Session ID cannot be empty")
        if not isinstance(self.player_id, str) or not self.player_id.strip():
            raise ValueError("Player ID cannot be empty")

        # Validate UUID format
        try:
            UUID(self.session_id)
            UUID(self.player_id)
        except ValueError as e:
            raise ValueError(f"Invalid UUID format: {e}")

    def __str__(self) -> str:
        return f"{self.session_id}:{self.player_id}"


@dataclass(frozen=True)
class SessionReference:
    """
    Reference to a poker session with external identification.

    Contains both internal and external identifiers for session tracking.
    """

    session_id: str
    external_id: str
    game_number: int

    def __post_init__(self) -> None:
        """Validate session reference data."""
        if not isinstance(self.session_id, str) or not self.session_id.strip():
            raise ValueError("Session ID cannot be empty")
        if not isinstance(self.external_id, str) or not self.external_id.strip():
            raise ValueError("External ID cannot be empty")
        if not isinstance(self.game_number, int) or self.game_number <= 0:
            raise ValueError("Game number must be a positive integer")

        # Validate session_id as UUID
        try:
            UUID(self.session_id)
        except ValueError as e:
            raise ValueError(f"Invalid session ID UUID format: {e}")

    def __str__(self) -> str:
        return f"Session {self.game_number} ({self.external_id})"


@dataclass(frozen=True)
class PlayerNames:
    """
    Player name information including both verified display name and session-specific aliases.

    The display_name is the verified player identity, while names contains the array
    of names used during the specific session.
    """

    display_name: str
    session_names: List[str]

    def __post_init__(self) -> None:
        """Validate player names data."""
        if not isinstance(self.display_name, str) or not self.display_name.strip():
            raise ValueError("Display name cannot be empty")
        if not isinstance(self.session_names, list):
            raise ValueError("Session names must be a list")
        if not self.session_names:
            raise ValueError("Session names list cannot be empty")

        # Validate all names are non-empty strings
        for name in self.session_names:
            if not isinstance(name, str) or not name.strip():
                raise ValueError("All session names must be non-empty strings")

    def get_primary_session_name(self) -> str:
        """Get the primary name used in the session (first in list)."""
        return self.session_names[0]

    def has_multiple_names(self) -> bool:
        """Check if player used multiple names during the session."""
        return len(self.session_names) > 1

    def contains_name(self, name: str) -> bool:
        """Check if a name appears in the session names."""
        return name in self.session_names

    def __str__(self) -> str:
        if self.has_multiple_names():
            return f"{self.display_name} (as {', '.join(self.session_names)})"
        return f"{self.display_name} (as {self.get_primary_session_name()})"


@dataclass(frozen=True)
class FinancialSummary:
    """
    Financial summary for a player's session participation.

    Contains all monetary values in chip units (cents).
    """

    buy_in_sum: int
    cash_out_sum: int
    in_game: int
    net: int

    def __post_init__(self) -> None:
        """Validate financial data and ensure consistency."""
        # Validate all values are integers (representing cents)
        for field_name, value in [
            ("buy_in_sum", self.buy_in_sum),
            ("cash_out_sum", self.cash_out_sum),
            ("in_game", self.in_game),
            ("net", self.net)
        ]:
            if not isinstance(value, int):
                raise TypeError(f"{field_name} must be an integer (cents)")

        # Validate business rule: net = cash_out + in_game - buy_in
        calculated_net = self.cash_out_sum + self.in_game - self.buy_in_sum
        if self.net != calculated_net:
            raise ValueError(
                f"Net amount ({self.net}) does not match calculated value "
                f"(cash_out: {self.cash_out_sum} + in_game: {self.in_game} - buy_in: {self.buy_in_sum} = {calculated_net})"
            )

    @classmethod
    def create(cls, buy_in_sum: int, cash_out_sum: int, in_game: int) -> FinancialSummary:
        """
        Create a FinancialSummary with automatically calculated net amount.

        Args:
            buy_in_sum: Total amount bought in (cents)
            cash_out_sum: Total amount cashed out (cents)
            in_game: Amount still in play (cents)

        Returns:
            FinancialSummary with calculated net
        """
        net = cash_out_sum + in_game - buy_in_sum
        return cls(
            buy_in_sum=buy_in_sum,
            cash_out_sum=cash_out_sum,
            in_game=in_game,
            net=net
        )

    def to_dollars(self) -> dict:
        """Convert all amounts to dollar values for display."""
        return {
            "buy_in_sum": self.buy_in_sum / 100.0,
            "cash_out_sum": self.cash_out_sum / 100.0,
            "in_game": self.in_game / 100.0,
            "net": self.net / 100.0
        }

    def is_profitable(self) -> bool:
        """Check if this session was profitable."""
        return self.net > 0

    def is_break_even(self) -> bool:
        """Check if this session was break-even."""
        return self.net == 0

    def is_losing(self) -> bool:
        """Check if this session was a loss."""
        return self.net < 0

    def with_updated_amounts(self, **kwargs) -> FinancialSummary:
        """
        Create a new FinancialSummary with updated amounts.

        Automatically recalculates net if buy_in, cash_out, or in_game change.
        """
        buy_in = kwargs.get('buy_in_sum', self.buy_in_sum)
        cash_out = kwargs.get('cash_out_sum', self.cash_out_sum)
        in_game = kwargs.get('in_game', self.in_game)

        return self.create(buy_in, cash_out, in_game)