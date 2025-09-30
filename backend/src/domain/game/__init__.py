"""
Game domain module.

Contains domain entities, value objects, and services for game summary and analytics functionality.
"""

from .entities import GameSummary, PlayerSummary, PlayerAnalytics, SessionExtreme
from .value_objects import WinStreak, LossStreak, SessionPerformance, PlayerRank
from .services import StreakCalculator, RankingCalculator, AnalyticsAggregator
from .repositories import GameSummaryRepository, SQLAlchemyGameSummaryRepository

__all__ = [
    # Entities
    'GameSummary',
    'PlayerSummary',
    'PlayerAnalytics',
    'SessionExtreme',

    # Value Objects
    'WinStreak',
    'LossStreak',
    'SessionPerformance',
    'PlayerRank',

    # Services
    'StreakCalculator',
    'RankingCalculator',
    'AnalyticsAggregator',

    # Repositories
    'GameSummaryRepository',
    'SQLAlchemyGameSummaryRepository',
]