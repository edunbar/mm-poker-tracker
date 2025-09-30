"""
Domain services for game and game summary business logic.

These services contain business rules and calculations that don't naturally
belong to a single entity or value object.
"""

from __future__ import annotations

import base64
import secrets
from typing import List, Dict, Tuple, Optional
from decimal import Decimal

from domain.poker.value_objects import Money, PlayerId, PublicCode, AdminToken, GameTitle
from domain.poker.exceptions import GameCreationError, RepositoryError
from .entities import Game, PlayerSummary, PlayerAnalytics, SessionExtreme
from .value_objects import (
    PlayerRank, WinStreak, LossStreak, SessionPerformance, PlayerStats
)
from .repositories import GameRepository


class GameCreationService:
    """
    Domain service for creating new games with proper business rules.

    This service encapsulates the complex logic of game creation including
    code generation, uniqueness validation, and retry mechanisms.
    """

    def __init__(self, game_repository: GameRepository):
        """
        Initialize the service with required dependencies.

        Args:
            game_repository: Repository for game persistence operations
        """
        self.game_repository = game_repository

    def create_game(
        self,
        title: Optional[str] = None,
        max_retries: int = 10
    ) -> Game:
        """
        Create a new game with generated codes and business rule validation.

        Args:
            title: Optional human-readable title for the game
            max_retries: Maximum attempts for code generation due to collisions

        Returns:
            A newly created Game entity

        Raises:
            ValueError: If title validation fails
            GameCreationError: If game creation fails after max retries
            RepositoryError: For persistence-related errors
        """
        # Validate and create title if provided
        game_title = None
        if title is not None:
            try:
                game_title = GameTitle(title)
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid title: {str(e)}")

        # Attempt to create game with unique codes
        for attempt in range(max_retries):
            try:
                # Generate codes using business rules
                public_code = self._generate_public_code()
                admin_token = self._generate_admin_token()

                # Check for uniqueness before creating entity
                if self.game_repository.public_code_exists(public_code):
                    continue  # Try again with new code

                if self.game_repository.admin_token_exists(admin_token):
                    continue  # Try again with new token

                # Create the game entity
                game = Game.create_new(
                    public_code=public_code,
                    admin_token=admin_token,
                    title=game_title
                )

                # Persist the game
                saved_game = self.game_repository.save(game)

                return saved_game

            except Exception as e:
                if attempt == max_retries - 1:
                    raise GameCreationError(
                        f"Failed to create game after {max_retries} attempts: {str(e)}"
                    )
                # Continue trying on intermediate attempts

        # This should never be reached due to the exception handling above
        raise GameCreationError("Failed to create game due to repeated code collisions")

    def _generate_public_code(self, length: int = 5) -> PublicCode:
        """
        Generate a public code using cryptographically secure random generation.

        Args:
            length: Length of the code to generate

        Returns:
            A new PublicCode instance
        """
        # Use base32 encoding for readability (excludes confusing characters)
        raw_code = base64.b32encode(secrets.token_bytes(length)).decode()
        # Remove padding and take only the required length
        clean_code = raw_code.strip("=").upper()[:length]

        return PublicCode(clean_code)

    def _generate_admin_token(self, nbytes: int = 32) -> AdminToken:
        """
        Generate an admin token using cryptographically secure random generation.

        Args:
            nbytes: Number of random bytes to use for token generation

        Returns:
            A new AdminToken instance
        """
        # Generate URL-safe token
        token_value = secrets.token_urlsafe(nbytes)
        return AdminToken(token_value)

    def validate_title(self, title: Optional[str]) -> Optional[GameTitle]:
        """
        Validate a game title according to business rules.

        Args:
            title: The title string to validate

        Returns:
            A GameTitle instance if valid, None if title is None

        Raises:
            ValueError: If the title is invalid
        """
        if title is None:
            return None

        try:
            return GameTitle(title)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid title: {str(e)}")


class RankingCalculator:
    """
    Service for calculating player rankings based on net winnings.

    Handles the business logic for determining player positions and handling ties.
    """

    @staticmethod
    def calculate_rankings(summaries: List[PlayerSummary]) -> List[PlayerSummary]:
        """
        Calculate rankings for a list of player summaries.

        Players are ranked by total net winnings (highest first).
        Players with the same net winnings receive the same rank.

        Args:
            summaries: List of PlayerSummary objects to rank

        Returns:
            List of PlayerSummary objects with updated rankings
        """
        if not summaries:
            return []

        # Sort by net winnings (descending) and then by name for consistent ordering
        sorted_summaries = sorted(
            summaries,
            key=lambda x: (-x.total_net.amount, x.player_name)
        )

        # Assign ranks using dense ranking (1, 1, 2, 3, 3, 4)
        ranked_summaries = []
        current_rank = 1

        for i, summary in enumerate(sorted_summaries):
            # If this is not the first player and net is different from previous
            if i > 0 and summary.total_net != sorted_summaries[i - 1].total_net:
                current_rank = i + 1

            # Create new summary with updated rank
            ranked_summary = PlayerSummary(
                player_id=summary.player_id,
                player_name=summary.player_name,
                rank=PlayerRank(current_rank),
                total_buy_in=summary.total_buy_in,
                total_cash_out=summary.total_cash_out,
                total_net=summary.total_net,
                games_played=summary.games_played
            )
            ranked_summaries.append(ranked_summary)

        return ranked_summaries

    @staticmethod
    def get_rank_for_net_amount(summaries: List[PlayerSummary], net_amount: Money) -> int:
        """
        Get the rank that a given net amount would have in the current standings.

        Args:
            summaries: Current player summaries
            net_amount: The net amount to find rank for

        Returns:
            The rank position this amount would have
        """
        if not summaries:
            return 1

        # Count how many players have better net winnings
        better_count = sum(1 for summary in summaries if summary.total_net > net_amount)
        return better_count + 1


class StreakCalculator:
    """
    Service for calculating winning and losing streaks.

    Handles the complex logic of determining current and historical streaks
    from session performance data.
    """

    @staticmethod
    def calculate_current_streaks(
        player_id: PlayerId,
        session_performances: List[SessionPerformance]
    ) -> Tuple[WinStreak, LossStreak]:
        """
        Calculate current winning and losing streaks for a player.

        Args:
            player_id: The player to calculate streaks for
            session_performances: List of session performances in chronological order

        Returns:
            Tuple of (current_winning_streak, current_losing_streak)
        """
        if not session_performances:
            return WinStreak(0, Money.zero()), LossStreak(0, Money.zero())

        # Start from the most recent session and work backwards
        current_winning_length = 0
        current_winning_net = Money.zero()
        current_losing_length = 0
        current_losing_net = Money.zero()

        # Process sessions in reverse chronological order
        for session in reversed(session_performances):
            if session.is_winning_session():
                if current_losing_length == 0:  # Still in winning streak
                    current_winning_length += 1
                    current_winning_net = current_winning_net + session.net_result
                else:
                    break  # Hit a loss, stop counting wins
            elif session.is_losing_session():
                if current_winning_length == 0:  # Still in losing streak
                    current_losing_length += 1
                    current_losing_net = current_losing_net + session.net_result
                else:
                    break  # Hit a win, stop counting losses
            else:
                # Break-even session breaks any streak
                break

        return (
            WinStreak(current_winning_length, current_winning_net),
            LossStreak(current_losing_length, current_losing_net)
        )

    @staticmethod
    def calculate_longest_streaks(
        player_id: PlayerId,
        session_performances: List[SessionPerformance]
    ) -> Tuple[WinStreak, LossStreak]:
        """
        Calculate the longest winning and losing streaks for a player.

        Args:
            player_id: The player to calculate streaks for
            session_performances: List of session performances in chronological order

        Returns:
            Tuple of (longest_winning_streak, longest_losing_streak)
        """
        if not session_performances:
            return WinStreak(0, Money.zero()), LossStreak(0, Money.zero())

        # Track current streak state
        current_win_length = 0
        current_win_net = Money.zero()
        current_loss_length = 0
        current_loss_net = Money.zero()

        # Track longest streaks found
        longest_win_length = 0
        longest_win_net = Money.zero()
        longest_loss_length = 0
        longest_loss_net = Money.zero()

        for session in session_performances:
            if session.is_winning_session():
                # Continue or start winning streak
                current_win_length += 1
                current_win_net = current_win_net + session.net_result

                # Reset losing streak
                current_loss_length = 0
                current_loss_net = Money.zero()

                # Check if this is the longest winning streak
                if current_win_length > longest_win_length:
                    longest_win_length = current_win_length
                    longest_win_net = current_win_net

            elif session.is_losing_session():
                # Continue or start losing streak
                current_loss_length += 1
                current_loss_net = current_loss_net + session.net_result

                # Reset winning streak
                current_win_length = 0
                current_win_net = Money.zero()

                # Check if this is the longest losing streak
                if current_loss_length > longest_loss_length:
                    longest_loss_length = current_loss_length
                    longest_loss_net = current_loss_net

            else:
                # Break-even session resets both streaks
                current_win_length = 0
                current_win_net = Money.zero()
                current_loss_length = 0
                current_loss_net = Money.zero()

        return (
            WinStreak(longest_win_length, longest_win_net),
            LossStreak(longest_loss_length, longest_loss_net)
        )

    @staticmethod
    def has_never_been_profitable(session_performances: List[SessionPerformance]) -> bool:
        """
        Check if a player has never had a profitable session.

        Args:
            session_performances: List of session performances

        Returns:
            True if player has never had a winning session
        """
        return not any(session.is_winning_session() for session in session_performances)


class AnalyticsAggregator:
    """
    Service for aggregating analytics data across multiple sessions.

    Handles the complex calculations needed for advanced player analytics.
    """

    @staticmethod
    def calculate_player_stats(session_performances: List[SessionPerformance]) -> PlayerStats:
        """
        Calculate aggregated statistics for a player.

        Args:
            session_performances: List of session performances

        Returns:
            PlayerStats object with aggregated data
        """
        if not session_performances:
            return PlayerStats(
                total_games=0,
                total_wins=0,
                total_losses=0,
                total_buy_in=Money.zero(),
                total_net=Money.zero(),
                never_profitable=True
            )

        total_games = len(session_performances)
        total_wins = sum(1 for session in session_performances if session.is_winning_session())
        total_losses = sum(1 for session in session_performances if session.is_losing_session())

        total_buy_in = Money.zero()
        total_net = Money.zero()

        for session in session_performances:
            total_buy_in = total_buy_in + session.buy_in
            total_net = total_net + session.net_result

        never_profitable = StreakCalculator.has_never_been_profitable(session_performances)

        return PlayerStats(
            total_games=total_games,
            total_wins=total_wins,
            total_losses=total_losses,
            total_buy_in=total_buy_in,
            total_net=total_net,
            never_profitable=never_profitable
        )

    @staticmethod
    def create_player_analytics(
        player_id: PlayerId,
        player_name: str,
        session_performances: List[SessionPerformance]
    ) -> PlayerAnalytics:
        """
        Create complete PlayerAnalytics from session performances.

        Args:
            player_id: The player ID
            player_name: The player name
            session_performances: List of session performances in chronological order

        Returns:
            Complete PlayerAnalytics object
        """
        stats = AnalyticsAggregator.calculate_player_stats(session_performances)

        current_win_streak, current_loss_streak = StreakCalculator.calculate_current_streaks(
            player_id, session_performances
        )

        longest_win_streak, longest_loss_streak = StreakCalculator.calculate_longest_streaks(
            player_id, session_performances
        )

        return PlayerAnalytics(
            player_id=player_id,
            player_name=player_name,
            stats=stats,
            current_winning_streak=current_win_streak,
            current_losing_streak=current_loss_streak,
            longest_winning_streak=longest_win_streak,
            longest_losing_streak=longest_loss_streak
        )

    @staticmethod
    def find_extreme_sessions(
        session_performances: List[SessionPerformance],
        limit: int = 25
    ) -> Tuple[List[SessionPerformance], List[SessionPerformance]]:
        """
        Find the best and worst session performances.

        Args:
            session_performances: All session performances to analyze
            limit: Maximum number of extremes to return for each type

        Returns:
            Tuple of (best_sessions, worst_sessions)
        """
        if not session_performances:
            return [], []

        # Filter to only winning and losing sessions
        winning_sessions = [s for s in session_performances if s.is_winning_session()]
        losing_sessions = [s for s in session_performances if s.is_losing_session()]

        # Sort by net result
        best_sessions = sorted(
            winning_sessions,
            key=lambda x: x.net_result.amount,
            reverse=True
        )[:limit]

        worst_sessions = sorted(
            losing_sessions,
            key=lambda x: x.net_result.amount
        )[:limit]

        return best_sessions, worst_sessions