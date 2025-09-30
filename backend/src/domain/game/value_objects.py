"""
Value objects for the game domain.

These immutable objects represent concepts like streaks, rankings, and performance metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from domain.poker.value_objects import Money


@dataclass(frozen=True)
class PlayerRank:
    """Represents a player's ranking position in a game."""

    position: int

    def __post_init__(self) -> None:
        """Validate rank position."""
        if self.position <= 0:
            raise ValueError("Rank position must be positive")

    def is_first_place(self) -> bool:
        """Check if this is first place."""
        return self.position == 1

    def is_top_three(self) -> bool:
        """Check if this rank is in the top 3."""
        return self.position <= 3


@dataclass(frozen=True)
class WinStreak:
    """Represents a winning streak for a player."""

    length: int
    total_net: Money

    def __post_init__(self) -> None:
        """Validate streak data."""
        if self.length < 0:
            raise ValueError("Streak length cannot be negative")
        if not isinstance(self.total_net, Money):
            raise TypeError("total_net must be a Money instance")

    def is_active(self) -> bool:
        """Check if this is an active streak (length > 0)."""
        return self.length > 0

    def average_per_session(self) -> Money:
        """Calculate average winnings per session in this streak."""
        if self.length == 0:
            return Money.zero()
        return self.total_net / self.length


@dataclass(frozen=True)
class LossStreak:
    """Represents a losing streak for a player."""

    length: int
    total_net: Money  # Will be negative

    def __post_init__(self) -> None:
        """Validate streak data."""
        if self.length < 0:
            raise ValueError("Streak length cannot be negative")
        if not isinstance(self.total_net, Money):
            raise TypeError("total_net must be a Money instance")

    def is_active(self) -> bool:
        """Check if this is an active streak (length > 0)."""
        return self.length > 0

    def average_per_session(self) -> Money:
        """Calculate average losses per session in this streak."""
        if self.length == 0:
            return Money.zero()
        return self.total_net / self.length


@dataclass(frozen=True)
class SessionPerformance:
    """Represents a single session's performance for a player."""

    game_number: Optional[int]
    session_name: str
    external_id: str
    net_result: Money
    buy_in: Money
    cash_out: Money
    in_game: Money

    def __post_init__(self) -> None:
        """Validate session performance data."""
        if self.game_number is not None and self.game_number <= 0:
            raise ValueError("Game number must be positive")
        if not self.session_name:
            raise ValueError("Session name cannot be empty")
        if not self.external_id:
            raise ValueError("External ID cannot be empty")

        # Validate Money instances
        for field_name, field_value in [
            ("net_result", self.net_result),
            ("buy_in", self.buy_in),
            ("cash_out", self.cash_out),
            ("in_game", self.in_game)
        ]:
            if not isinstance(field_value, Money):
                raise TypeError(f"{field_name} must be a Money instance")

    def is_winning_session(self) -> bool:
        """Check if this was a winning session."""
        return self.net_result.is_positive()

    def is_losing_session(self) -> bool:
        """Check if this was a losing session."""
        return self.net_result < Money.zero()

    def is_break_even_session(self) -> bool:
        """Check if this was a break-even session."""
        return self.net_result.is_zero()

    def roi_percentage(self) -> Decimal:
        """Calculate return on investment as a percentage."""
        if self.buy_in.is_zero():
            return Decimal('0')

        # ROI = (net_result / buy_in) * 100
        roi = (self.net_result.amount / self.buy_in.amount) * Decimal('100')
        return roi.quantize(Decimal('0.01'))


@dataclass(frozen=True)
class PlayerStats:
    """Aggregated statistics for a player across all sessions."""

    total_games: int
    total_wins: int
    total_losses: int
    total_buy_in: Money
    total_net: Money
    never_profitable: bool

    def __post_init__(self) -> None:
        """Validate player stats."""
        if self.total_games < 0:
            raise ValueError("Total games cannot be negative")
        if self.total_wins < 0:
            raise ValueError("Total wins cannot be negative")
        if self.total_losses < 0:
            raise ValueError("Total losses cannot be negative")
        if self.total_wins + self.total_losses > self.total_games:
            raise ValueError("Wins + losses cannot exceed total games")

        if not isinstance(self.total_buy_in, Money):
            raise TypeError("total_buy_in must be a Money instance")
        if not isinstance(self.total_net, Money):
            raise TypeError("total_net must be a Money instance")

    @property
    def total_break_even(self) -> int:
        """Calculate number of break-even games."""
        return self.total_games - self.total_wins - self.total_losses

    def win_rate(self) -> Decimal:
        """Calculate win rate as a percentage."""
        if self.total_games == 0:
            return Decimal('0')
        return (Decimal(self.total_wins) / Decimal(self.total_games) * Decimal('100')).quantize(Decimal('0.1'))

    def loss_rate(self) -> Decimal:
        """Calculate loss rate as a percentage."""
        if self.total_games == 0:
            return Decimal('0')
        return (Decimal(self.total_losses) / Decimal(self.total_games) * Decimal('100')).quantize(Decimal('0.1'))

    def break_even_rate(self) -> Decimal:
        """Calculate break-even rate as a percentage."""
        if self.total_games == 0:
            return Decimal('0')
        return (Decimal(self.total_break_even) / Decimal(self.total_games) * Decimal('100')).quantize(Decimal('0.1'))

    def average_buy_in(self) -> Money:
        """Calculate average buy-in per game."""
        if self.total_games == 0:
            return Money.zero()
        return self.total_buy_in / self.total_games

    def average_net_per_game(self) -> Money:
        """Calculate average net result per game."""
        if self.total_games == 0:
            return Money.zero()
        return self.total_net / self.total_games

    def roi_percentage(self) -> Decimal:
        """Calculate overall return on investment as a percentage."""
        if self.total_buy_in.is_zero():
            return Decimal('0')

        roi = (self.total_net.amount / self.total_buy_in.amount) * Decimal('100')
        return roi.quantize(Decimal('0.1'))