"""Poker domain module containing entities, value objects, and business logic."""

from .entities.poker_session import PokerSession, SessionState
from .value_objects import (
    Money,
    SessionId,
    PlayerId,
    GameId,
    Hand,
    SessionDuration,
    SessionStats,
)
from .exceptions import (
    PokerDomainError,
    SessionAlreadyEndedError,
    InvalidCashOutAmountError,
    SessionExpiredError,
    MaximumHandsExceededError,
    DuplicateHandNumberError,
    InvalidSessionStateError,
    NegativeMoneyAmountError,
    SessionNotFoundError,
)
from .events import (
    DomainEvent,
    SessionStartedEvent,
    SessionEndedEvent,
    LargeWinEvent,
    HandAddedEvent,
    MarathonSessionEvent,
    SessionAutoEndedEvent,
    DomainEventCollector,
)
from .repositories import (
    PokerSessionRepository,
    RepositoryError,
    SessionNotFoundError as RepoSessionNotFoundError,
    SessionAlreadyExistsError,
    RepositoryConnectionError,
)

__all__ = [
    # Entities
    "PokerSession",
    "SessionState",
    # Value Objects
    "Money",
    "SessionId",
    "PlayerId",
    "GameId",
    "Hand",
    "SessionDuration",
    "SessionStats",
    # Exceptions
    "PokerDomainError",
    "SessionAlreadyEndedError",
    "InvalidCashOutAmountError",
    "SessionExpiredError",
    "MaximumHandsExceededError",
    "DuplicateHandNumberError",
    "InvalidSessionStateError",
    "NegativeMoneyAmountError",
    "SessionNotFoundError",
    # Events
    "DomainEvent",
    "SessionStartedEvent",
    "SessionEndedEvent",
    "LargeWinEvent",
    "HandAddedEvent",
    "MarathonSessionEvent",
    "SessionAutoEndedEvent",
    "DomainEventCollector",
    # Repositories
    "PokerSessionRepository",
    "RepositoryError",
    "RepoSessionNotFoundError",
    "SessionAlreadyExistsError",
    "RepositoryConnectionError",
]