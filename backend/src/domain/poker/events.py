"""
Domain events for the poker domain.

Domain events represent something that happened in the domain that domain experts care about.
They enable loose coupling between bounded contexts and support event-driven architecture.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from .value_objects import SessionId, PlayerId, GameId, Money, SessionDuration, SessionStats


class DomainEvent(ABC):
    """
    Base class for all domain events.

    Domain events are immutable records of something that happened in the domain.
    They carry the minimal data needed to describe what occurred.
    """

    def __init__(self) -> None:
        self.event_id: str = str(uuid4())
        self.occurred_at: datetime = datetime.utcnow()

    @abstractmethod
    def event_type(self) -> str:
        """Return the type identifier for this event."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type(),
            'occurred_at': self.occurred_at.isoformat(),
        }


@dataclass
class SessionStartedEvent(DomainEvent):
    """Event raised when a poker session is started."""

    session_id: SessionId
    player_id: PlayerId
    game_id: GameId
    buy_in_amount: Money
    session_type: str
    session_name: str | None = None

    def event_type(self) -> str:
        return "poker.session.started"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'session_id': str(self.session_id),
            'player_id': str(self.player_id),
            'game_id': str(self.game_id),
            'buy_in_amount': str(self.buy_in_amount.amount),
            'session_type': self.session_type,
            'session_name': self.session_name,
        })
        return data


@dataclass
class SessionEndedEvent(DomainEvent):
    """Event raised when a poker session is ended."""

    session_id: SessionId
    player_id: PlayerId
    game_id: GameId
    buy_in_amount: Money
    cash_out_amount: Money
    profit: Money
    duration: SessionDuration
    session_stats: SessionStats
    ended_at: datetime = field(default_factory=datetime.utcnow)

    def event_type(self) -> str:
        return "poker.session.ended"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'session_id': str(self.session_id),
            'player_id': str(self.player_id),
            'game_id': str(self.game_id),
            'buy_in_amount': str(self.buy_in_amount.amount),
            'cash_out_amount': str(self.cash_out_amount.amount),
            'profit': str(self.profit.amount),
            'duration_minutes': self.duration.minutes,
            'total_hands': self.session_stats.total_hands,
            'winning_hands': self.session_stats.winning_hands,
            'ended_at': self.ended_at.isoformat(),
        })
        return data


@dataclass
class LargeWinEvent(DomainEvent):
    """Event raised when a player achieves a large win (profit > threshold)."""

    session_id: SessionId
    player_id: PlayerId
    game_id: GameId
    profit: Money
    threshold: Money
    buy_in_amount: Money
    cash_out_amount: Money

    def event_type(self) -> str:
        return "poker.session.large_win"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'session_id': str(self.session_id),
            'player_id': str(self.player_id),
            'game_id': str(self.game_id),
            'profit': str(self.profit.amount),
            'threshold': str(self.threshold.amount),
            'buy_in_amount': str(self.buy_in_amount.amount),
            'cash_out_amount': str(self.cash_out_amount.amount),
        })
        return data


@dataclass
class HandAddedEvent(DomainEvent):
    """Event raised when a hand is added to a session."""

    session_id: SessionId
    player_id: PlayerId
    hand_number: int
    pot_size: Money
    player_result: Money

    def event_type(self) -> str:
        return "poker.hand.added"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'session_id': str(self.session_id),
            'player_id': str(self.player_id),
            'hand_number': self.hand_number,
            'pot_size': str(self.pot_size.amount),
            'player_result': str(self.player_result.amount),
        })
        return data


@dataclass
class MarathonSessionEvent(DomainEvent):
    """Event raised when a session becomes a marathon session (>12 hours)."""

    session_id: SessionId
    player_id: PlayerId
    game_id: GameId
    duration: SessionDuration
    current_profit: Money

    def event_type(self) -> str:
        return "poker.session.marathon"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'session_id': str(self.session_id),
            'player_id': str(self.player_id),
            'game_id': str(self.game_id),
            'duration_minutes': self.duration.minutes,
            'duration_hours': self.duration.to_hours(),
            'current_profit': str(self.current_profit.amount),
        })
        return data


@dataclass
class SessionAutoEndedEvent(DomainEvent):
    """Event raised when a session is automatically ended due to expiration."""

    session_id: SessionId
    player_id: PlayerId
    game_id: GameId
    reason: str
    duration: SessionDuration

    def event_type(self) -> str:
        return "poker.session.auto_ended"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'session_id': str(self.session_id),
            'player_id': str(self.player_id),
            'game_id': str(self.game_id),
            'reason': self.reason,
            'duration_minutes': self.duration.minutes,
        })
        return data


class DomainEventCollector:
    """
    Collects domain events during business operations.

    This follows the pattern of collecting events during domain operations
    and then publishing them after successful persistence.
    """

    def __init__(self) -> None:
        self._events: list[DomainEvent] = []

    def add_event(self, event: DomainEvent) -> None:
        """Add a domain event to the collection."""
        self._events.append(event)

    def get_events(self) -> list[DomainEvent]:
        """Get all collected events."""
        return self._events.copy()

    def clear_events(self) -> None:
        """Clear all collected events."""
        self._events.clear()

    def has_events(self) -> bool:
        """Check if there are any collected events."""
        return len(self._events) > 0