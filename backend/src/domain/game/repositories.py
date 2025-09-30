"""
Repository interfaces and implementations for game and game summary data access.

Provides abstraction over data access for games, game summaries, analytics, and session extremes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
from decimal import Decimal

from sqlalchemy.orm import Session as DBSession
from sqlalchemy import text

from domain.poker.value_objects import Money, GameId, PlayerId, PublicCode, AdminToken
from .entities import Game, GameSummary, PlayerSummary, PlayerAnalytics, SessionExtreme
from .value_objects import PlayerRank, SessionPerformance, WinStreak, LossStreak, PlayerStats


class GameRepository(ABC):
    """Abstract repository for core Game entity operations."""

    @abstractmethod
    def save(self, game: Game) -> Game:
        """
        Save a game entity to persistent storage.

        Args:
            game: The Game entity to save

        Returns:
            The saved Game entity (may include generated fields)

        Raises:
            DuplicatePublicCodeError: If public code already exists
            DuplicateAdminTokenError: If admin token already exists
            RepositoryError: For other persistence errors
        """
        pass

    @abstractmethod
    def get_by_id(self, game_id: GameId) -> Optional[Game]:
        """
        Retrieve a game by its unique identifier.

        Args:
            game_id: The unique game identifier

        Returns:
            The Game entity if found, None otherwise
        """
        pass

    @abstractmethod
    def get_by_public_code(self, public_code: PublicCode) -> Optional[Game]:
        """
        Retrieve a game by its public code.

        Args:
            public_code: The public sharing code

        Returns:
            The Game entity if found, None otherwise
        """
        pass

    @abstractmethod
    def get_by_admin_token(self, admin_token: AdminToken) -> Optional[Game]:
        """
        Retrieve a game by its admin token.

        Args:
            admin_token: The administrative access token

        Returns:
            The Game entity if found, None otherwise
        """
        pass

    @abstractmethod
    def public_code_exists(self, public_code: PublicCode) -> bool:
        """
        Check if a public code is already in use.

        Args:
            public_code: The public code to check

        Returns:
            True if the code exists, False otherwise
        """
        pass

    @abstractmethod
    def admin_token_exists(self, admin_token: AdminToken) -> bool:
        """
        Check if an admin token is already in use.

        Args:
            admin_token: The admin token to check

        Returns:
            True if the token exists, False otherwise
        """
        pass

    @abstractmethod
    def update(self, game: Game) -> Game:
        """
        Update an existing game entity.

        Args:
            game: The Game entity with updated data

        Returns:
            The updated Game entity

        Raises:
            GameNotFoundError: If the game doesn't exist
            RepositoryError: For other persistence errors
        """
        pass

    @abstractmethod
    def delete(self, game_id: GameId) -> bool:
        """
        Delete a game and all related data.

        Args:
            game_id: The unique game identifier

        Returns:
            True if the game was deleted, False if it didn't exist

        Raises:
            RepositoryError: For persistence errors during deletion
        """
        pass


class GameSummaryRepository(ABC):
    """Abstract repository for game summary data access."""

    @abstractmethod
    def get_game_title(self, game_id: GameId) -> Optional[str]:
        """Get the title of a game by its public code."""
        pass

    @abstractmethod
    def get_player_summaries_data(self, game_id: GameId) -> List[Dict]:
        """Get raw player summary data for a game."""
        pass

    @abstractmethod
    def get_session_performances_data(self, game_id: GameId) -> List[Dict]:
        """Get session performance data for analytics calculations."""
        pass

    @abstractmethod
    def get_session_extremes_data(self, game_id: GameId) -> List[Dict]:
        """Get best and worst session performance data."""
        pass


class SQLAlchemyGameSummaryRepository(GameSummaryRepository):
    """SQLAlchemy implementation of the game summary repository."""

    def __init__(self, db_session: DBSession):
        """Initialize with database session."""
        self._db_session = db_session

    def get_game_title(self, game_id: GameId) -> Optional[str]:
        """Get the title of a game by its UUID."""
        game_title_sql = text(
            "SELECT title FROM games WHERE id = :game_id LIMIT 1;"
        )
        result = self._db_session.execute(
            game_title_sql, {"game_id": str(game_id)}
        ).fetchone()

        return result[0] if result and result[0] else None

    def get_player_summaries_data(self, game_id: GameId) -> List[Dict]:
        """Get raw player summary data for a game."""
        sql = text('''
            WITH base AS (
                SELECT
                    p.id                         AS player_id,
                    p.display_name               AS player,
                    SUM(sps.buy_in_sum)          AS buy_in_chips,
                    SUM(sps.cash_out_sum)        AS cash_out_chips,
                    SUM(sps.in_game)             AS in_game_chips,
                    COUNT(DISTINCT s.id)         AS games_played
                FROM session_player_summaries sps
                JOIN sessions s      ON s.id = sps.session_id
                JOIN games g         ON g.id = s.game_id
                JOIN players p       ON p.id = sps.player_id
                WHERE g.id = :game_id
                GROUP BY p.id, p.display_name
            ),
            calc AS (
                SELECT
                    player_id,
                    player,
                    buy_in_chips,
                    cash_out_chips,
                    in_game_chips,
                    games_played,
                    (cash_out_chips + in_game_chips - buy_in_chips) AS total_net_chips
                FROM base
            )
            SELECT
                player_id,
                player,
                buy_in_chips,
                cash_out_chips,
                in_game_chips,
                total_net_chips,
                games_played
            FROM calc
            ORDER BY total_net_chips DESC, player;
        ''')

        rows = self._db_session.execute(sql, {"game_id": str(game_id)}).mappings().all()
        return [dict(row) for row in rows]

    def get_session_performances_data(self, game_id: GameId) -> List[Dict]:
        """Get session performance data for analytics calculations."""
        sql = text('''
            SELECT
                p.id AS player_id,
                p.display_name AS player_name,
                s.game_number,
                s.session_name,
                s.external_id,
                sps.net,
                sps.buy_in_sum,
                sps.cash_out_sum,
                sps.in_game,
                CASE WHEN sps.net > 0 THEN 1 ELSE 0 END AS is_win,
                CASE WHEN sps.net < 0 THEN 1 ELSE 0 END AS is_loss
            FROM session_player_summaries sps
            JOIN sessions s ON s.id = sps.session_id
            JOIN games g ON g.id = s.game_id
            JOIN players p ON p.id = sps.player_id
            WHERE g.id = :game_id
            ORDER BY p.id, s.game_number
        ''')

        rows = self._db_session.execute(sql, {"game_id": str(game_id)}).mappings().all()
        return [dict(row) for row in rows]

    def get_session_extremes_data(self, game_id: GameId) -> List[Dict]:
        """Get best and worst session performance data."""
        sql = text('''
            WITH session_performances AS (
                SELECT
                    p.id AS player_id,
                    p.display_name AS player_name,
                    s.game_number,
                    s.session_name,
                    s.external_id,
                    sps.net,
                    sps.buy_in_sum,
                    sps.cash_out_sum,
                    sps.in_game,
                    ROW_NUMBER() OVER (ORDER BY sps.net DESC) AS best_rank,
                    ROW_NUMBER() OVER (ORDER BY sps.net ASC) AS worst_rank
                FROM session_player_summaries sps
                JOIN sessions s ON s.id = sps.session_id
                JOIN games g ON g.id = s.game_id
                JOIN players p ON p.id = sps.player_id
                WHERE g.id = :game_id
            ),
            combined_results AS (
                SELECT
                    'best' as type,
                    player_id,
                    player_name,
                    game_number,
                    session_name,
                    external_id,
                    net,
                    buy_in_sum,
                    cash_out_sum,
                    in_game
                FROM session_performances
                WHERE best_rank <= 25 AND net > 0

                UNION ALL

                SELECT
                    'worst' as type,
                    player_id,
                    player_name,
                    game_number,
                    session_name,
                    external_id,
                    net,
                    buy_in_sum,
                    cash_out_sum,
                    in_game
                FROM session_performances
                WHERE worst_rank <= 25 AND net < 0
            )
            SELECT * FROM combined_results
            ORDER BY
                type DESC,
                CASE WHEN type = 'best' THEN -net ELSE net END ASC
        ''')

        rows = self._db_session.execute(sql, {"game_id": str(game_id)}).mappings().all()
        return [dict(row) for row in rows]

    def build_game_summary(self, game_id: GameId) -> GameSummary:
        """
        Build a complete GameSummary from database data.

        This method orchestrates the data retrieval and domain object creation.
        """
        # Get basic game information
        title = self.get_game_title(game_id)

        # Create the game summary aggregate root
        game_summary = GameSummary(game_id=game_id, title=title)

        # Build player summaries
        summaries_data = self.get_player_summaries_data(game_id)
        player_summaries = self._build_player_summaries(summaries_data)

        # Calculate rankings - import locally to avoid circular import
        from .services import RankingCalculator
        ranked_summaries = RankingCalculator.calculate_rankings(player_summaries)

        # Add summaries to game summary
        for summary in ranked_summaries:
            game_summary.add_player_summary(summary)

        # Build analytics data
        session_data = self.get_session_performances_data(game_id)
        analytics_dict = self._build_player_analytics(session_data)

        # Add analytics to game summary
        for analytics in analytics_dict.values():
            game_summary.add_player_analytics(analytics)

        # Build session extremes
        extremes_data = self.get_session_extremes_data(game_id)
        extremes = self._build_session_extremes(extremes_data)

        # Add extremes to game summary
        for extreme in extremes:
            game_summary.add_session_extreme(extreme)

        return game_summary

    def _build_player_summaries(self, summaries_data: List[Dict]) -> List[PlayerSummary]:
        """Build PlayerSummary objects from raw data."""
        summaries = []

        for row in summaries_data:
            # Include in_game chips in total_cash_out (money still on table)
            total_cash_out_cents = row['cash_out_chips'] + row['in_game_chips']

            summary = PlayerSummary(
                player_id=PlayerId(str(row['player_id'])),
                player_name=row['player'],
                rank=PlayerRank(1),  # Will be recalculated by RankingCalculator
                total_buy_in=Money(Decimal(row['buy_in_chips']) / 100),
                total_cash_out=Money(Decimal(total_cash_out_cents) / 100),
                total_net=Money(Decimal(row['total_net_chips']) / 100),
                games_played=row['games_played']
            )
            summaries.append(summary)

        return summaries

    def _build_player_analytics(self, session_data: List[Dict]) -> Dict[str, PlayerAnalytics]:
        """Build PlayerAnalytics objects from session performance data."""
        # Group sessions by player
        player_sessions = {}
        player_names = {}

        for row in session_data:
            player_id = str(row['player_id'])
            if player_id not in player_sessions:
                player_sessions[player_id] = []
                player_names[player_id] = row['player_name']

            # Create SessionPerformance
            session_perf = SessionPerformance(
                game_number=row['game_number'],
                session_name=row['session_name'] or f"Session {row['game_number']}",
                external_id=row['external_id'],
                net_result=Money(Decimal(row['net']) / 100),
                buy_in=Money(Decimal(row['buy_in_sum']) / 100),
                cash_out=Money(Decimal(row['cash_out_sum']) / 100),
                in_game=Money(Decimal(row['in_game']) / 100)
            )
            player_sessions[player_id].append(session_perf)

        # Build analytics for each player
        analytics_dict = {}
        for player_id, sessions in player_sessions.items():
            # Import locally to avoid circular import
            from .services import AnalyticsAggregator
            analytics = AnalyticsAggregator.create_player_analytics(
                player_id=PlayerId(player_id),
                player_name=player_names[player_id],
                session_performances=sessions
            )
            analytics_dict[player_id] = analytics

        return analytics_dict

    def _build_session_extremes(self, extremes_data: List[Dict]) -> List[SessionExtreme]:
        """Build SessionExtreme objects from raw data."""
        extremes = []

        for row in extremes_data:
            session_perf = SessionPerformance(
                game_number=row['game_number'],
                session_name=row['session_name'] or f"Session {row['game_number']}",
                external_id=row['external_id'],
                net_result=Money(Decimal(row['net']) / 100),
                buy_in=Money(Decimal(row['buy_in_sum']) / 100),
                cash_out=Money(Decimal(row['cash_out_sum']) / 100),
                in_game=Money(Decimal(row['in_game']) / 100)
            )

            extreme = SessionExtreme(
                player_id=PlayerId(str(row['player_id'])),
                player_name=row['player_name'],
                session_performance=session_perf,
                extreme_type=row['type']
            )
            extremes.append(extreme)

        return extremes