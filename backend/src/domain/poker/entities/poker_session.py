"""
PokerSession domain entity.

This is the core business entity for poker sessions. It contains all the business logic
and rules related to poker sessions, separated from infrastructure concerns.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional

from ..events import (
    DomainEventCollector,
    SessionStartedEvent,
    SessionEndedEvent,
    LargeWinEvent,
    HandAddedEvent,
    MarathonSessionEvent,
    SessionAutoEndedEvent,
)
from ..exceptions import (
    SessionAlreadyEndedError,
    InvalidCashOutAmountError,
    SessionExpiredError,
    MaximumHandsExceededError,
    DuplicateHandNumberError,
    InvalidSessionStateError,
)
from ..value_objects import (
    SessionId,
    PlayerId,
    GameId,
    Money,
    Hand,
    SessionDuration,
    SessionStats,
)


class SessionState(Enum):
    """Enumeration of possible session states."""

    ACTIVE = "active"
    ENDED = "ended"
    EXPIRED = "expired"


class PokerSession:
    """
    Core domain entity representing a poker session.

    A poker session represents a single player's participation in a poker game,
    including their buy-in, hands played, and eventual cash-out.
    """

    # Business constants
    MAX_SESSION_HOURS = 24
    MAX_HANDS_PER_SESSION = 1000
    LARGE_WIN_THRESHOLD = Money(1000)
    MARATHON_SESSION_HOURS = 12

    def __init__(
        self,
        session_id: SessionId,
        player_id: PlayerId,
        game_id: GameId,
        buy_in_amount: Money,
        session_type: str,
        session_name: str | None = None,
        created_at: datetime | None = None,
    ) -> None:
        """
        Initialize a new poker session.

        Args:
            session_id: Unique identifier for the session
            player_id: ID of the player participating
            game_id: ID of the game this session belongs to
            buy_in_amount: Amount the player bought in for
            session_type: Type of session (e.g., "cash_game", "tournament")
            session_name: Optional name for the session
            created_at: When the session was created (defaults to now)

        Raises:
            ValueError: If any business rules are violated
        """
        # Validate inputs
        if not isinstance(session_id, SessionId):
            raise ValueError("session_id must be a SessionId instance")
        if not isinstance(player_id, PlayerId):
            raise ValueError("player_id must be a PlayerId instance")
        if not isinstance(game_id, GameId):
            raise ValueError("game_id must be a GameId instance")
        if not isinstance(buy_in_amount, Money):
            raise ValueError("buy_in_amount must be a Money instance")
        if not buy_in_amount.is_positive():
            raise ValueError("Buy-in amount must be positive")
        if not session_type.strip():
            raise ValueError("Session type cannot be empty")

        # Initialize state
        self._session_id = session_id
        self._player_id = player_id
        self._game_id = game_id
        self._buy_in_amount = buy_in_amount
        self._session_type = session_type.strip()
        self._session_name = session_name.strip() if session_name else None
        self._created_at = created_at or datetime.utcnow()

        # Session state
        self._state = SessionState.ACTIVE
        self._ended_at: Optional[datetime] = None
        self._cash_out_amount: Optional[Money] = None

        # Hands tracking
        self._hands: Dict[int, Hand] = {}

        # Domain events
        self._event_collector = DomainEventCollector()

        # Raise session started event
        self._event_collector.add_event(
            SessionStartedEvent(
                session_id=self._session_id,
                player_id=self._player_id,
                game_id=self._game_id,
                buy_in_amount=self._buy_in_amount,
                session_type=self._session_type,
                session_name=self._session_name,
            )
        )

    # Properties
    @property
    def session_id(self) -> SessionId:
        """Get the session ID."""
        return self._session_id

    @property
    def player_id(self) -> PlayerId:
        """Get the player ID."""
        return self._player_id

    @property
    def game_id(self) -> GameId:
        """Get the game ID."""
        return self._game_id

    @property
    def buy_in_amount(self) -> Money:
        """Get the buy-in amount."""
        return self._buy_in_amount

    @property
    def cash_out_amount(self) -> Optional[Money]:
        """Get the cash-out amount (None if session not ended)."""
        return self._cash_out_amount

    @property
    def session_type(self) -> str:
        """Get the session type."""
        return self._session_type

    @property
    def session_name(self) -> Optional[str]:
        """Get the session name."""
        return self._session_name

    @property
    def created_at(self) -> datetime:
        """Get when the session was created."""
        return self._created_at

    @property
    def ended_at(self) -> Optional[datetime]:
        """Get when the session ended (None if still active)."""
        return self._ended_at

    @property
    def state(self) -> SessionState:
        """Get the current session state."""
        return self._state

    @property
    def domain_events(self) -> List:
        """Get the collected domain events."""
        return self._event_collector.get_events()

    def clear_events(self) -> None:
        """Clear collected domain events."""
        self._event_collector.clear_events()

    # Business logic methods
    def add_hand(self, hand: Hand) -> None:
        """
        Add a hand to the session.

        Args:
            hand: The hand to add

        Raises:
            SessionAlreadyEndedError: If session is already ended
            MaximumHandsExceededError: If maximum hands exceeded
            DuplicateHandNumberError: If hand number already exists
            SessionExpiredError: If session has expired
        """
        self._ensure_session_is_active()
        self._check_session_expiry()

        if len(self._hands) >= self.MAX_HANDS_PER_SESSION:
            raise MaximumHandsExceededError(len(self._hands), self.MAX_HANDS_PER_SESSION)

        if hand.hand_number in self._hands:
            raise DuplicateHandNumberError(hand.hand_number)

        # Add the hand
        self._hands[hand.hand_number] = hand

        # Raise hand added event
        self._event_collector.add_event(
            HandAddedEvent(
                session_id=self._session_id,
                player_id=self._player_id,
                hand_number=hand.hand_number,
                pot_size=hand.pot_size,
                player_result=hand.player_result,
            )
        )

        # Check for marathon session
        self._check_marathon_session()

    def end_session(self, cash_out_amount: Money) -> None:
        """
        End the poker session.

        Args:
            cash_out_amount: The amount the player cashed out

        Raises:
            SessionAlreadyEndedError: If session is already ended
            InvalidCashOutAmountError: If cash out amount is invalid
        """
        self._ensure_session_is_active()

        if not isinstance(cash_out_amount, Money):
            raise InvalidCashOutAmountError(cash_out_amount, "Must be a Money instance")

        # Set session end state
        self._cash_out_amount = cash_out_amount
        self._ended_at = datetime.utcnow()
        self._state = SessionState.ENDED

        # Calculate derived values
        profit = self.calculate_profit()
        duration = self.get_duration()
        stats = self.get_session_stats()

        # Raise session ended event
        self._event_collector.add_event(
            SessionEndedEvent(
                session_id=self._session_id,
                player_id=self._player_id,
                game_id=self._game_id,
                buy_in_amount=self._buy_in_amount,
                cash_out_amount=cash_out_amount,
                profit=profit,
                duration=duration,
                session_stats=stats,
                ended_at=self._ended_at,
            )
        )

        # Check for large win
        if profit >= self.LARGE_WIN_THRESHOLD:
            self._event_collector.add_event(
                LargeWinEvent(
                    session_id=self._session_id,
                    player_id=self._player_id,
                    game_id=self._game_id,
                    profit=profit,
                    threshold=self.LARGE_WIN_THRESHOLD,
                    buy_in_amount=self._buy_in_amount,
                    cash_out_amount=cash_out_amount,
                )
            )

    def calculate_profit(self) -> Money:
        """
        Calculate the profit/loss for this session.

        Returns:
            Profit as Money (positive for profit, zero for break-even)

        Raises:
            InvalidSessionStateError: If session hasn't ended yet
        """
        if self._cash_out_amount is None:
            # For active sessions, calculate current profit from hands
            return self._calculate_hands_profit()

        # For ended sessions, use cash-out amount
        return Money(self._cash_out_amount.amount - self._buy_in_amount.amount)

    def _calculate_hands_profit(self) -> Money:
        """Calculate profit from hands played so far."""
        total_result = Money.zero()
        for hand in self._hands.values():
            total_result = total_result + hand.player_result
        return total_result

    def calculate_hourly_rate(self) -> Money:
        """
        Calculate the hourly rate for this session.

        Returns:
            Hourly rate as Money

        Raises:
            InvalidSessionStateError: If session hasn't ended yet
            ValueError: If session duration is zero
        """
        if not self.is_ended():
            raise InvalidSessionStateError(
                str(self._session_id),
                self._state.value,
                "ended"
            )

        duration = self.get_duration()
        profit = self.calculate_profit()
        hours = duration.to_hours()

        # Handle zero or very small duration gracefully
        if hours <= 0:
            return Money.zero()

        return Money(str(profit.amount / Decimal(str(hours))))

    def is_profitable(self) -> bool:
        """Check if the session is profitable."""
        try:
            profit = self.calculate_profit()
            return profit.is_positive()
        except InvalidSessionStateError:
            # For active sessions, check hands profit
            return self._calculate_hands_profit().is_positive()

    def is_ended(self) -> bool:
        """Check if the session has ended."""
        return self._state == SessionState.ENDED

    def is_active(self) -> bool:
        """Check if the session is active."""
        return self._state == SessionState.ACTIVE

    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return self._state == SessionState.EXPIRED

    def get_duration(self) -> SessionDuration:
        """Get the session duration."""
        from datetime import timezone

        # Always work with timezone-aware UTC datetimes for consistency
        if self._ended_at:
            # Session is ended - use the ended time
            end_time = self._ended_at
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)
        else:
            # Session is still active - use current UTC time
            end_time = datetime.now(timezone.utc)

        # Ensure created_at is timezone-aware
        created_at = self._created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        # Calculate duration
        delta = end_time - created_at
        duration_minutes = int(delta.total_seconds() / 60)

        # Ensure duration is non-negative (handle edge cases)
        if duration_minutes < 0:
            duration_minutes = 0

        return SessionDuration(duration_minutes)

    def get_session_stats(self) -> SessionStats:
        """Get aggregated statistics for this session."""
        total_hands = len(self._hands)
        winning_hands = sum(1 for hand in self._hands.values() if hand.is_winning_hand())
        break_even_hands = sum(1 for hand in self._hands.values() if hand.is_break_even_hand())
        total_pot_value = sum((hand.pot_size for hand in self._hands.values()), Money.zero())

        return SessionStats(
            total_hands=total_hands,
            winning_hands=winning_hands,
            break_even_hands=break_even_hands,
            total_pot_value=total_pot_value,
        )

    def get_hands(self) -> List[Hand]:
        """Get all hands played in this session."""
        return sorted(self._hands.values(), key=lambda h: h.hand_number)

    def get_hand_count(self) -> int:
        """Get the number of hands played."""
        return len(self._hands)

    def auto_end_if_expired(self) -> bool:
        """
        Automatically end session if it has expired.

        Returns:
            True if session was auto-ended, False otherwise
        """
        if not self.is_active():
            return False

        duration = self.get_duration()
        if duration.to_hours() >= self.MAX_SESSION_HOURS:
            # Auto-end with current profit as cash-out
            current_profit = self._calculate_hands_profit()
            cash_out = self._buy_in_amount + current_profit

            self._cash_out_amount = cash_out
            self._ended_at = datetime.utcnow()
            self._state = SessionState.EXPIRED

            self._event_collector.add_event(
                SessionAutoEndedEvent(
                    session_id=self._session_id,
                    player_id=self._player_id,
                    game_id=self._game_id,
                    reason=f"Exceeded maximum duration of {self.MAX_SESSION_HOURS} hours",
                    duration=duration,
                )
            )

            return True

        return False

    # Private helper methods
    def _ensure_session_is_active(self) -> None:
        """Ensure the session is in active state."""
        if not self.is_active():
            raise SessionAlreadyEndedError(str(self._session_id))

    def _check_session_expiry(self) -> None:
        """Check if session has expired and raise error if so."""
        duration = self.get_duration()
        if duration.to_hours() >= self.MAX_SESSION_HOURS:
            raise SessionExpiredError(str(self._session_id), self.MAX_SESSION_HOURS)

    def _check_marathon_session(self) -> None:
        """Check if this has become a marathon session and raise event."""
        duration = self.get_duration()
        if duration.to_hours() >= self.MARATHON_SESSION_HOURS:
            # Only raise event once when crossing threshold
            # (In practice, you might want to track this state to avoid duplicate events)
            current_profit = self._calculate_hands_profit()
            self._event_collector.add_event(
                MarathonSessionEvent(
                    session_id=self._session_id,
                    player_id=self._player_id,
                    game_id=self._game_id,
                    duration=duration,
                    current_profit=current_profit,
                )
            )

    def __eq__(self, other: object) -> bool:
        """Check equality based on session ID."""
        if not isinstance(other, PokerSession):
            return False
        return self._session_id == other._session_id

    def __hash__(self) -> int:
        """Make sessions hashable based on session ID."""
        return hash(self._session_id)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"PokerSession(id={self._session_id}, player={self._player_id}, "
            f"state={self._state.value}, hands={len(self._hands)})"
        )