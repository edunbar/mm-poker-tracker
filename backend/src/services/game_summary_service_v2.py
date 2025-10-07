"""
Domain-based GameSummaryService v2

Direct replacement for game_summary_service.py using domain layer.
Maintains exact API compatibility while using clean domain architecture.
Includes caching and performance monitoring from the original service.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session as DBSession

from db.database import SessionLocal
from domain.poker.value_objects import GameId
from domain.game.repositories import SQLAlchemyGameSummaryRepository
from middleware.performance_monitor import monitor_performance, record_cache_hit, record_cache_miss

logger = logging.getLogger(__name__)

# Simple in-memory cache for analytics data (same as original service)
_analytics_cache = {}
_cache_ttl = 300  # 5 minutes TTL


def _get_cache_key(public_code: str, query_type: str) -> str:
    """Generate cache key for the given public code and query type."""
    return f"{query_type}:{public_code}"


def _is_cache_valid(cache_entry: Dict) -> bool:
    """Check if cache entry is still valid based on TTL."""
    return time.time() - cache_entry['timestamp'] < _cache_ttl


def _get_from_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get data from cache if valid, otherwise return None."""
    if cache_key in _analytics_cache:
        entry = _analytics_cache[cache_key]
        if _is_cache_valid(entry):
            logging.debug(f"Cache hit for {cache_key}")
            # Record cache hit for monitoring
            cache_type = cache_key.split(':')[0]
            record_cache_hit(cache_type)
            return entry['data']
        else:
            # Remove expired entry
            del _analytics_cache[cache_key]
            logging.debug(f"Cache expired for {cache_key}")

    # Record cache miss for monitoring
    cache_type = cache_key.split(':')[0]
    record_cache_miss(cache_type)
    return None


def _set_cache(cache_key: str, data: Dict[str, Any]) -> None:
    """Store data in cache with timestamp."""
    _analytics_cache[cache_key] = {
        'data': data,
        'timestamp': time.time()
    }
    logging.debug(f"Cached data for {cache_key}")


def invalidate_game_cache(public_code: str) -> None:
    """Invalidate all cached data for a specific game."""
    keys_to_remove = []
    for key in _analytics_cache.keys():
        if key.endswith(f":{public_code}"):
            keys_to_remove.append(key)

    for key in keys_to_remove:
        del _analytics_cache[key]
        logging.debug(f"Invalidated cache for {key}")


def clear_all_cache() -> None:
    """Clear entire analytics cache."""
    global _analytics_cache
    _analytics_cache = {}
    logging.debug("Cleared entire analytics cache")


@monitor_performance('summary')
def get_player_summaries(public_code: str) -> Dict[str, Any]:
    """
    Get player summaries for a game - maintains compatibility with legacy service.

    Args:
        public_code: The game's public code

    Returns:
        Dictionary with 'title' and 'rows' keys, matching legacy format
    """
    # Check cache first
    cache_key = _get_cache_key(public_code, "summaries")
    cached_data = _get_from_cache(cache_key)
    if cached_data is not None:
        return cached_data

    # Use domain repository to get data
    with SessionLocal() as db:
        # First lookup game by public code to get the actual game UUID
        from db.models import Game
        game = db.query(Game).filter(Game.public_code == public_code).first()
        if not game:
            # Raise error for non-existent games
            raise ValueError(f"Game not found with code: {public_code}")

        repository = SQLAlchemyGameSummaryRepository(db)
        game_id = GameId(str(game.id))  # Use the actual UUID
        game_summary = repository.build_game_summary(game_id)

        logger.info(f"Built game summary for {public_code}, found {len(game_summary.player_summaries)} player summaries")

        # Convert domain objects to legacy format
        rows = []
        for summary in game_summary.player_summaries:
            rows.append({
                "player": summary.player_name,
                "rank": summary.rank.position,
                "buyIn": float(summary.total_buy_in.amount),
                "cashOut": float(summary.total_cash_out.amount),
                "net": float(summary.total_net.amount),
                "gamesPlayed": summary.games_played
            })

        result = {
            "title": game_summary.title,
            "rows": rows
        }

        # Cache the result
        _set_cache(cache_key, result)
        return result


@monitor_performance('analytics')
def get_player_analytics(public_code: str) -> Dict[str, Any]:
    """
    Get advanced analytics including streak calculations for a game.
    Maintains compatibility with legacy service.

    Args:
        public_code: The game's public code

    Returns:
        Dictionary with 'analytics' key containing player analytics data
    """
    # Check cache first
    cache_key = _get_cache_key(public_code, "analytics")
    cached_data = _get_from_cache(cache_key)
    if cached_data is not None:
        return cached_data

    # Use domain repository to get data
    with SessionLocal() as db:
        # First lookup game by public code to get the actual game UUID
        from db.models import Game
        game = db.query(Game).filter(Game.public_code == public_code).first()
        if not game:
            # Raise error for non-existent games
            raise ValueError(f"Game not found with code: {public_code}")

        repository = SQLAlchemyGameSummaryRepository(db)
        game_id = GameId(str(game.id))  # Use the actual UUID
        game_summary = repository.build_game_summary(game_id)

        # Convert domain analytics to legacy format
        player_analytics = {}
        for player_id, analytics in game_summary.player_analytics.items():
            player_analytics[player_id] = {
                'player_name': analytics.player_name,
                'total_games': analytics.stats.total_games,
                'total_wins': analytics.stats.total_wins,
                'total_losses': analytics.stats.total_losses,
                'current_losing_streak': analytics.current_losing_streak.length,
                'longest_losing_streak': analytics.longest_losing_streak.length,
                'current_winning_streak': analytics.current_winning_streak.length,
                'longest_winning_streak': analytics.longest_winning_streak.length,
                'never_profitable': analytics.stats.never_profitable,
                'total_net': int(analytics.stats.total_net.amount * 100),  # Convert to cents
                'total_buy_in': int(analytics.stats.total_buy_in.amount * 100),  # Convert to cents
                'longest_winning_streak_net': int(analytics.longest_winning_streak.total_net.amount * 100),
                'longest_losing_streak_net': int(analytics.longest_losing_streak.total_net.amount * 100),
            }

        result = {"analytics": player_analytics}

        # Cache the result
        _set_cache(cache_key, result)
        return result


@monitor_performance('session_extremes')
def get_session_extremes(public_code: str) -> Dict[str, Any]:
    """
    Get the actual best and worst single session performances.
    Maintains compatibility with legacy service.

    Args:
        public_code: The game's public code

    Returns:
        Dictionary with 'best_sessions' and 'worst_sessions' keys
    """
    # Check cache first
    cache_key = _get_cache_key(public_code, "session_extremes")
    cached_data = _get_from_cache(cache_key)
    if cached_data is not None:
        return cached_data

    # Use domain repository to get data
    with SessionLocal() as db:
        # First lookup game by public code to get the actual game UUID
        from db.models import Game
        game = db.query(Game).filter(Game.public_code == public_code).first()
        if not game:
            # Raise error for non-existent games
            raise ValueError(f"Game not found with code: {public_code}")

        repository = SQLAlchemyGameSummaryRepository(db)
        game_id = GameId(str(game.id))  # Use the actual UUID
        game_summary = repository.build_game_summary(game_id)

        # Convert domain extremes to legacy format
        best_sessions = []
        worst_sessions = []

        for extreme in game_summary.best_sessions:
            session_data = {
                'player_name': extreme.player_name,
                'game_number': extreme.session_performance.game_number,
                'session_name': extreme.session_performance.session_name,
                'external_id': extreme.session_performance.external_id,
                'net': int(extreme.session_performance.net_result.amount * 100),  # Convert to cents
                'buy_in_sum': int(extreme.session_performance.buy_in.amount * 100),
                'cash_out_sum': int(extreme.session_performance.cash_out.amount * 100),
                'in_game': int(extreme.session_performance.in_game.amount * 100)
            }
            best_sessions.append(session_data)

        for extreme in game_summary.worst_sessions:
            session_data = {
                'player_name': extreme.player_name,
                'game_number': extreme.session_performance.game_number,
                'session_name': extreme.session_performance.session_name,
                'external_id': extreme.session_performance.external_id,
                'net': int(extreme.session_performance.net_result.amount * 100),  # Convert to cents
                'buy_in_sum': int(extreme.session_performance.buy_in.amount * 100),
                'cash_out_sum': int(extreme.session_performance.cash_out.amount * 100),
                'in_game': int(extreme.session_performance.in_game.amount * 100)
            }
            worst_sessions.append(session_data)

        result = {
            "best_sessions": best_sessions,
            "worst_sessions": worst_sessions
        }

        # Cache the result
        _set_cache(cache_key, result)
        return result


class GameSummaryService:
    """
    Domain-based GameSummaryService that replaces the old direct database access approach.

    Uses domain entities and repositories while maintaining exact API compatibility
    with existing Flask routes.
    """

    def __init__(self, db_session: DBSession):
        """
        Initialize with required database session.

        Args:
            db_session: SQLAlchemy session (REQUIRED). Session lifecycle is managed
                       by the caller (typically the web layer).

        Raises:
            ValueError: If db_session is None
        """
        if db_session is None:
            raise ValueError("db_session is required - services do not manage sessions")

        self._db_session = db_session
        self._repository = SQLAlchemyGameSummaryRepository(self._db_session)

    def get_player_summaries(self, public_code: str) -> Dict[str, Any]:
        """Get player summaries using the domain repository."""
        return get_player_summaries(public_code)

    def get_player_analytics(self, public_code: str) -> Dict[str, Any]:
        """Get player analytics using the domain repository."""
        return get_player_analytics(public_code)

    def get_session_extremes(self, public_code: str) -> Dict[str, Any]:
        """Get session extremes using the domain repository."""
        return get_session_extremes(public_code)

    def get_game_summary_domain_object(self, public_code: str) -> Any:
        """
        Get the full domain GameSummary object.

        This method is unique to the v2 service and provides access to the
        rich domain model for consumers that want to work with domain objects.

        Args:
            public_code: The game's public code

        Returns:
            GameSummary domain object or None if game not found
        """
        # First lookup game by public code to get the actual game UUID
        from db.models import Game
        game = self._db_session.query(Game).filter(Game.public_code == public_code).first()
        if not game:
            return None

        game_id = GameId(str(game.id))  # Use the actual UUID
        return self._repository.build_game_summary(game_id)

    def invalidate_cache(self, public_code: str) -> None:
        """Invalidate cached data for a specific game."""
        invalidate_game_cache(public_code)

    def clear_all_caches(self) -> None:
        """Clear all cached data."""
        clear_all_cache()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        return {
            'total_entries': len(_analytics_cache),
            'cache_ttl_seconds': _cache_ttl,
            'entries': list(_analytics_cache.keys())
        }