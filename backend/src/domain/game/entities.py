"""
Domain entities for the game domain.

These represent the core business objects for games, game summaries, and analytics.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime, timezone
from uuid import UUID, uuid4

from domain.poker.value_objects import Money, GameId, PlayerId, PublicCode, AdminToken, GameTitle
from .value_objects import PlayerRank, WinStreak, LossStreak, SessionPerformance, PlayerStats


@dataclass
class Game:
    """
    Core Game entity representing a long-lived poker game container.

    A game serves as a collection point for multiple poker sessions and players.
    It has both a public code for sharing and an admin token for management.
    This is the aggregate root for game-related operations.
    """

    id: GameId
    public_code: PublicCode
    admin_token: AdminToken
    title: Optional[GameTitle] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate game entity data."""
        if not isinstance(self.id, GameId):
            raise TypeError("id must be a GameId instance")
        if not isinstance(self.public_code, PublicCode):
            raise TypeError("public_code must be a PublicCode instance")
        if not isinstance(self.admin_token, AdminToken):
            raise TypeError("admin_token must be an AdminToken instance")
        if self.title is not None and not isinstance(self.title, GameTitle):
            raise TypeError("title must be a GameTitle instance or None")
        if not isinstance(self.created_at, datetime):
            raise TypeError("created_at must be a datetime instance")
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary")

        # Ensure created_at has timezone info
        if self.created_at.tzinfo is None:
            object.__setattr__(self, 'created_at', self.created_at.replace(tzinfo=timezone.utc))

    @classmethod
    def create_new(
        cls,
        public_code: PublicCode,
        admin_token: AdminToken,
        title: Optional[GameTitle] = None,
        metadata: Optional[Dict[str, any]] = None
    ) -> Game:
        """
        Factory method to create a new Game with generated ID.

        Args:
            public_code: The public sharing code for the game
            admin_token: The administrative access token
            title: Optional human-readable title
            metadata: Optional additional metadata

        Returns:
            A new Game instance with generated UUID
        """
        game_id = GameId(str(uuid4()))
        return cls(
            id=game_id,
            public_code=public_code,
            admin_token=admin_token,
            title=title,
            metadata=metadata or {}
        )

    def has_title(self) -> bool:
        """Check if the game has a title set."""
        return self.title is not None

    def get_display_name(self) -> str:
        """Get the display name for the game (title or public code)."""
        if self.has_title():
            return str(self.title)
        return f"Game {self.public_code}"

    def is_admin_token_valid(self, token: str) -> bool:
        """Verify if the provided token matches the admin token."""
        return self.admin_token.value == token

    def update_title(self, new_title: Optional[GameTitle]) -> Game:
        """
        Create a new Game instance with updated title.

        Returns a new instance to maintain immutability.
        """
        return replace(self, title=new_title)

    def add_metadata(self, key: str, value: any) -> Game:
        """
        Create a new Game instance with additional metadata.

        Returns a new instance to maintain immutability.
        """
        new_metadata = self.metadata.copy()
        new_metadata[key] = value
        return replace(self, metadata=new_metadata)

    def remove_metadata(self, key: str) -> Game:
        """
        Create a new Game instance with metadata key removed.

        Returns a new instance to maintain immutability.
        """
        new_metadata = self.metadata.copy()
        new_metadata.pop(key, None)
        return replace(self, metadata=new_metadata)

    def get_metadata(self, key: str, default: any = None) -> any:
        """Get a metadata value by key."""
        return self.metadata.get(key, default)

    def get_age_in_days(self) -> int:
        """Calculate the age of the game in days."""
        now = datetime.now(timezone.utc)
        delta = now - self.created_at
        return delta.days

    def is_recent(self, days: int = 7) -> bool:
        """Check if the game was created within the specified number of days."""
        return self.get_age_in_days() <= days

    def __str__(self) -> str:
        return f"Game({self.public_code} - {self.get_display_name()})"


@dataclass
class PlayerSummary:
    """
    Represents a player's summary statistics within a game.

    This is a core entity that encapsulates all summary data for a single player
    across all sessions in a specific game.
    """

    player_id: PlayerId
    player_name: str
    rank: PlayerRank
    total_buy_in: Money
    total_cash_out: Money
    total_net: Money
    games_played: int

    def __post_init__(self) -> None:
        """Validate player summary data."""
        if not self.player_name.strip():
            raise ValueError("Player name cannot be empty")
        if self.games_played < 0:
            raise ValueError("Games played cannot be negative")
        if not isinstance(self.player_id, PlayerId):
            raise TypeError("player_id must be a PlayerId instance")
        if not isinstance(self.rank, PlayerRank):
            raise TypeError("rank must be a PlayerRank instance")

        # Validate Money instances
        for field_name, field_value in [
            ("total_buy_in", self.total_buy_in),
            ("total_cash_out", self.total_cash_out),
            ("total_net", self.total_net)
        ]:
            if not isinstance(field_value, Money):
                raise TypeError(f"{field_name} must be a Money instance")

    def is_profitable(self) -> bool:
        """Check if this player is profitable overall."""
        return self.total_net.is_positive()

    def is_losing(self) -> bool:
        """Check if this player is losing overall."""
        return self.total_net < Money.zero()

    def roi_percentage(self) -> Decimal:
        """Calculate return on investment as a percentage."""
        if self.total_buy_in.is_zero():
            return Decimal('0')

        roi = (self.total_net.amount / self.total_buy_in.amount) * Decimal('100')
        return roi.quantize(Decimal('0.1'))

    def average_net_per_game(self) -> Money:
        """Calculate average net result per game."""
        if self.games_played == 0:
            return Money.zero()
        return self.total_net / self.games_played


@dataclass
class PlayerAnalytics:
    """
    Advanced analytics for a player including streaks and detailed statistics.

    This entity provides deeper insights into a player's performance patterns.
    """

    player_id: PlayerId
    player_name: str
    stats: PlayerStats
    current_winning_streak: WinStreak
    current_losing_streak: LossStreak
    longest_winning_streak: WinStreak
    longest_losing_streak: LossStreak

    def __post_init__(self) -> None:
        """Validate player analytics data."""
        if not self.player_name.strip():
            raise ValueError("Player name cannot be empty")
        if not isinstance(self.player_id, PlayerId):
            raise TypeError("player_id must be a PlayerId instance")
        if not isinstance(self.stats, PlayerStats):
            raise TypeError("stats must be a PlayerStats instance")

        # Validate streak instances
        streak_fields = [
            ("current_winning_streak", self.current_winning_streak, WinStreak),
            ("current_losing_streak", self.current_losing_streak, LossStreak),
            ("longest_winning_streak", self.longest_winning_streak, WinStreak),
            ("longest_losing_streak", self.longest_losing_streak, LossStreak)
        ]

        for field_name, field_value, expected_type in streak_fields:
            if not isinstance(field_value, expected_type):
                raise TypeError(f"{field_name} must be a {expected_type.__name__} instance")

    def is_currently_on_winning_streak(self) -> bool:
        """Check if player is currently on a winning streak."""
        return self.current_winning_streak.is_active()

    def is_currently_on_losing_streak(self) -> bool:
        """Check if player is currently on a losing streak."""
        return self.current_losing_streak.is_active()

    def has_never_been_profitable(self) -> bool:
        """Check if player has never had a profitable session."""
        return self.stats.never_profitable

    def get_current_streak_description(self) -> str:
        """Get a human-readable description of the current streak."""
        if self.is_currently_on_winning_streak():
            return f"Winning {self.current_winning_streak.length} in a row"
        elif self.is_currently_on_losing_streak():
            return f"Losing {self.current_losing_streak.length} in a row"
        else:
            return "No active streak"


@dataclass
class SessionExtreme:
    """
    Represents an extreme session performance (best or worst).

    Used to track the highest and lowest single-session performances.
    """

    player_id: PlayerId
    player_name: str
    session_performance: SessionPerformance
    extreme_type: str  # 'best' or 'worst'

    def __post_init__(self) -> None:
        """Validate session extreme data."""
        if not self.player_name.strip():
            raise ValueError("Player name cannot be empty")
        if self.extreme_type not in ['best', 'worst']:
            raise ValueError("extreme_type must be 'best' or 'worst'")
        if not isinstance(self.player_id, PlayerId):
            raise TypeError("player_id must be a PlayerId instance")
        if not isinstance(self.session_performance, SessionPerformance):
            raise TypeError("session_performance must be a SessionPerformance instance")

    def is_best_performance(self) -> bool:
        """Check if this is a best performance record."""
        return self.extreme_type == 'best'

    def is_worst_performance(self) -> bool:
        """Check if this is a worst performance record."""
        return self.extreme_type == 'worst'


@dataclass
class GameSummary:
    """
    Aggregate root for game summary data.

    This is the main entity that contains all summary information for a specific game,
    including player summaries, analytics, and extreme performances.
    """

    game_id: GameId
    title: Optional[str]
    player_summaries: List[PlayerSummary] = field(default_factory=list)
    player_analytics: Dict[str, PlayerAnalytics] = field(default_factory=dict)
    best_sessions: List[SessionExtreme] = field(default_factory=list)
    worst_sessions: List[SessionExtreme] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate game summary data."""
        if not isinstance(self.game_id, GameId):
            raise TypeError("game_id must be a GameId instance")

        # Validate that all player summaries are valid
        for summary in self.player_summaries:
            if not isinstance(summary, PlayerSummary):
                raise TypeError("All player_summaries must be PlayerSummary instances")

        # Validate analytics dictionary
        for player_id, analytics in self.player_analytics.items():
            if not isinstance(analytics, PlayerAnalytics):
                raise TypeError("All player_analytics values must be PlayerAnalytics instances")

        # Validate extreme sessions
        for session in self.best_sessions + self.worst_sessions:
            if not isinstance(session, SessionExtreme):
                raise TypeError("All extreme sessions must be SessionExtreme instances")

    def get_player_summary(self, player_id: PlayerId) -> Optional[PlayerSummary]:
        """Get summary for a specific player."""
        for summary in self.player_summaries:
            if summary.player_id == player_id:
                return summary
        return None

    def get_player_analytics(self, player_id: PlayerId) -> Optional[PlayerAnalytics]:
        """Get analytics for a specific player."""
        return self.player_analytics.get(str(player_id))

    def get_top_players(self, limit: int = 5) -> List[PlayerSummary]:
        """Get the top N players by rank."""
        sorted_summaries = sorted(self.player_summaries, key=lambda x: x.rank.position)
        return sorted_summaries[:limit]

    def get_profitable_players(self) -> List[PlayerSummary]:
        """Get all players who are profitable."""
        return [summary for summary in self.player_summaries if summary.is_profitable()]

    def get_losing_players(self) -> List[PlayerSummary]:
        """Get all players who are losing."""
        return [summary for summary in self.player_summaries if summary.is_losing()]

    def get_total_money_in_play(self) -> Money:
        """Calculate total money that has been bought in across all players."""
        total = Money.zero()
        for summary in self.player_summaries:
            total = total + summary.total_buy_in
        return total

    def get_player_count(self) -> int:
        """Get the total number of players in this game."""
        return len(self.player_summaries)

    def add_player_summary(self, summary: PlayerSummary) -> None:
        """Add a player summary to the game."""
        if not isinstance(summary, PlayerSummary):
            raise TypeError("summary must be a PlayerSummary instance")

        # Check if player already exists and update if so
        for i, existing_summary in enumerate(self.player_summaries):
            if existing_summary.player_id == summary.player_id:
                self.player_summaries[i] = summary
                return

        # Add new summary
        self.player_summaries.append(summary)

    def add_player_analytics(self, analytics: PlayerAnalytics) -> None:
        """Add player analytics to the game."""
        if not isinstance(analytics, PlayerAnalytics):
            raise TypeError("analytics must be a PlayerAnalytics instance")

        self.player_analytics[str(analytics.player_id)] = analytics

    def add_session_extreme(self, extreme: SessionExtreme) -> None:
        """Add a session extreme performance to the appropriate list."""
        if not isinstance(extreme, SessionExtreme):
            raise TypeError("extreme must be a SessionExtreme instance")

        if extreme.is_best_performance():
            self.best_sessions.append(extreme)
        else:
            self.worst_sessions.append(extreme)