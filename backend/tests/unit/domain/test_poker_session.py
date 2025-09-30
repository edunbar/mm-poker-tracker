"""
Unit tests for PokerSession domain entity.

These tests verify all business rules and behavior of the PokerSession entity,
including state transitions, business logic, and domain event generation.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from domain.poker.entities.poker_session import PokerSession, SessionState
from domain.poker.value_objects import (
    SessionId,
    PlayerId,
    GameId,
    Money,
    Hand,
    SessionDuration,
)
from domain.poker.exceptions import (
    SessionAlreadyEndedError,
    InvalidCashOutAmountError,
    SessionExpiredError,
    MaximumHandsExceededError,
    DuplicateHandNumberError,
    InvalidSessionStateError,
)
from domain.poker.events import (
    SessionStartedEvent,
    SessionEndedEvent,
    LargeWinEvent,
    HandAddedEvent,
    MarathonSessionEvent,
    SessionAutoEndedEvent,
)


class TestPokerSessionCreation:
    """Test cases for PokerSession creation and initialization."""

    def test_create_poker_session_with_valid_data(self):
        """Test creating a PokerSession with valid data."""
        session_id = SessionId.generate()
        player_id = PlayerId(str(SessionId.generate().value))
        game_id = GameId("ABCDE")
        buy_in = Money("100.00")

        session = PokerSession(
            session_id=session_id,
            player_id=player_id,
            game_id=game_id,
            buy_in_amount=buy_in,
            session_type="cash_game",
            session_name="Friday Night Game",
        )

        # Verify properties
        assert session.session_id == session_id
        assert session.player_id == player_id
        assert session.game_id == game_id
        assert session.buy_in_amount == buy_in
        assert session.session_type == "cash_game"
        assert session.session_name == "Friday Night Game"
        assert session.state == SessionState.ACTIVE
        assert session.cash_out_amount is None
        assert session.ended_at is None

        # Should generate SessionStartedEvent
        events = session.domain_events
        assert len(events) == 1
        assert isinstance(events[0], SessionStartedEvent)

    def test_create_poker_session_invalid_types(self):
        """Test that PokerSession validates parameter types."""
        session_id = SessionId.generate()
        player_id = PlayerId(str(SessionId.generate().value))
        game_id = GameId("ABCDE")

        with pytest.raises(ValueError, match="session_id must be a SessionId instance"):
            PokerSession("invalid", player_id, game_id, Money("100"), "cash")

        with pytest.raises(ValueError, match="player_id must be a PlayerId instance"):
            PokerSession(session_id, "invalid", game_id, Money("100"), "cash")

        with pytest.raises(ValueError, match="game_id must be a GameId instance"):
            PokerSession(session_id, player_id, "invalid", Money("100"), "cash")

        with pytest.raises(ValueError, match="buy_in_amount must be a Money instance"):
            PokerSession(session_id, player_id, game_id, 100.00, "cash")

    def test_create_poker_session_invalid_buy_in(self):
        """Test that PokerSession rejects non-positive buy-in amounts."""
        session_id = SessionId.generate()
        player_id = PlayerId(str(SessionId.generate().value))
        game_id = GameId("ABCDE")

        with pytest.raises(ValueError, match="Buy-in amount must be positive"):
            PokerSession(session_id, player_id, game_id, Money.zero(), "cash")

    def test_create_poker_session_empty_session_type(self):
        """Test that PokerSession rejects empty session type."""
        session_id = SessionId.generate()
        player_id = PlayerId(str(SessionId.generate().value))
        game_id = GameId("ABCDE")

        with pytest.raises(ValueError, match="Session type cannot be empty"):
            PokerSession(session_id, player_id, game_id, Money("100"), "")


class TestPokerSessionHandManagement:
    """Test cases for hand management in PokerSession."""

    def create_test_session(self) -> PokerSession:
        """Create a test session for hand management tests."""
        session = PokerSession(
            session_id=SessionId.generate(),
            player_id=PlayerId(str(SessionId.generate().value)),
            game_id=GameId("ABCDE"),
            buy_in_amount=Money("100.00"),
            session_type="cash_game",
        )
        session.clear_events()  # Clear creation events for clean testing
        return session

    def test_add_hand_to_session(self):
        """Test adding a hand to a session."""
        session = self.create_test_session()
        hand = Hand(
            hand_number=1,
            pot_size=Money("50.00"),
            player_result=Money("25.00")
        )

        session.add_hand(hand)

        assert session.get_hand_count() == 1
        hands = session.get_hands()
        assert len(hands) == 1
        assert hands[0] == hand

        # Should generate HandAddedEvent
        events = session.domain_events
        assert len(events) == 1
        assert isinstance(events[0], HandAddedEvent)

    def test_add_multiple_hands(self):
        """Test adding multiple hands to a session."""
        session = self.create_test_session()

        hand1 = Hand(1, Money("50.00"), Money("25.00"))
        hand2 = Hand(2, Money("75.00"), Money.zero())
        hand3 = Hand(3, Money("100.00"), Money("50.00"))

        session.add_hand(hand1)
        session.add_hand(hand2)
        session.add_hand(hand3)

        assert session.get_hand_count() == 3
        hands = session.get_hands()

        # Hands should be sorted by hand number
        assert hands[0].hand_number == 1
        assert hands[1].hand_number == 2
        assert hands[2].hand_number == 3

    def test_add_hand_duplicate_number(self):
        """Test that adding a hand with duplicate number raises error."""
        session = self.create_test_session()
        hand1 = Hand(1, Money("50.00"), Money("25.00"))
        hand2 = Hand(1, Money("75.00"), Money("30.00"))  # Same hand number

        session.add_hand(hand1)

        with pytest.raises(DuplicateHandNumberError):
            session.add_hand(hand2)

    def test_add_hand_to_ended_session(self):
        """Test that adding a hand to an ended session raises error."""
        session = self.create_test_session()
        session.end_session(Money("150.00"))

        hand = Hand(1, Money("50.00"), Money("25.00"))

        with pytest.raises(SessionAlreadyEndedError):
            session.add_hand(hand)

    def test_add_hand_maximum_hands_exceeded(self):
        """Test that adding more than maximum hands raises error."""
        session = self.create_test_session()

        # Add maximum allowed hands
        for i in range(PokerSession.MAX_HANDS_PER_SESSION):
            hand = Hand(i + 1, Money("50.00"), Money("5.00"))
            session.add_hand(hand)

        # Adding one more should fail
        overflow_hand = Hand(PokerSession.MAX_HANDS_PER_SESSION + 1, Money("50.00"), Money("5.00"))

        with pytest.raises(MaximumHandsExceededError):
            session.add_hand(overflow_hand)


class TestPokerSessionEndSession:
    """Test cases for ending poker sessions."""

    def create_test_session(self) -> PokerSession:
        """Create a test session for ending tests."""
        session = PokerSession(
            session_id=SessionId.generate(),
            player_id=PlayerId(str(SessionId.generate().value)),
            game_id=GameId("ABCDE"),
            buy_in_amount=Money("100.00"),
            session_type="cash_game",
        )
        session.clear_events()
        return session

    def test_end_session_successfully(self):
        """Test successfully ending a session."""
        session = self.create_test_session()
        cash_out = Money("150.00")

        session.end_session(cash_out)

        assert session.is_ended()
        assert session.cash_out_amount == cash_out
        assert session.ended_at is not None
        assert session.state == SessionState.ENDED

        # Should generate SessionEndedEvent
        events = session.domain_events
        session_ended_events = [e for e in events if isinstance(e, SessionEndedEvent)]
        assert len(session_ended_events) == 1

    def test_end_session_with_large_win(self):
        """Test ending a session with a large win generates LargeWinEvent."""
        session = self.create_test_session()
        # Cash out with large profit (> $1000 threshold)
        cash_out = Money("1200.00")  # $1100 profit

        session.end_session(cash_out)

        events = session.domain_events
        large_win_events = [e for e in events if isinstance(e, LargeWinEvent)]
        assert len(large_win_events) == 1

        large_win_event = large_win_events[0]
        assert large_win_event.profit == Money("1100.00")

    def test_end_session_already_ended(self):
        """Test that ending an already ended session raises error."""
        session = self.create_test_session()
        session.end_session(Money("150.00"))

        with pytest.raises(SessionAlreadyEndedError):
            session.end_session(Money("200.00"))

    def test_end_session_invalid_cash_out_type(self):
        """Test that ending session with invalid cash out type raises error."""
        session = self.create_test_session()

        with pytest.raises(InvalidCashOutAmountError):
            session.end_session(150.00)  # Not a Money instance


class TestPokerSessionBusinessLogic:
    """Test cases for business logic calculations."""

    def create_test_session_with_hands(self) -> PokerSession:
        """Create a test session with some hands for calculation tests."""
        session = PokerSession(
            session_id=SessionId.generate(),
            player_id=PlayerId(str(SessionId.generate().value)),
            game_id=GameId("ABCDE"),
            buy_in_amount=Money("100.00"),
            session_type="cash_game",
        )

        # Add some hands
        session.add_hand(Hand(1, Money("50.00"), Money("25.00")))  # Win
        session.add_hand(Hand(2, Money("75.00"), Money.zero()))    # Break even
        session.add_hand(Hand(3, Money("60.00"), Money("30.00")))  # Win

        session.clear_events()
        return session

    def test_calculate_profit_active_session(self):
        """Test calculating profit for active session based on hands."""
        session = self.create_test_session_with_hands()

        # Profit should be sum of hand results: 25 + 0 + 30 = 55
        profit = session.calculate_profit()
        assert profit == Money("55.00")

    def test_calculate_profit_ended_session(self):
        """Test calculating profit for ended session based on cash out."""
        session = self.create_test_session_with_hands()
        session.end_session(Money("180.00"))

        # Profit should be cash_out - buy_in: 180 - 100 = 80
        profit = session.calculate_profit()
        assert profit == Money("80.00")

    def test_calculate_hourly_rate(self):
        """Test calculating hourly rate for ended session."""
        # Create session with specific creation time
        created_at = datetime(2023, 1, 1, 10, 0, 0)
        session = PokerSession(
            session_id=SessionId.generate(),
            player_id=PlayerId(str(SessionId.generate().value)),
            game_id=GameId("ABCDE"),
            buy_in_amount=Money("100.00"),
            session_type="cash_game",
            created_at=created_at,
        )

        # End session 2 hours later
        session._ended_at = created_at + timedelta(hours=2)
        session._cash_out_amount = Money("150.00")
        session._state = SessionState.ENDED

        hourly_rate = session.calculate_hourly_rate()
        assert hourly_rate == Money("25.00")  # $50 profit / 2 hours

    def test_calculate_hourly_rate_active_session(self):
        """Test that calculating hourly rate for active session raises error."""
        session = self.create_test_session_with_hands()

        with pytest.raises(InvalidSessionStateError):
            session.calculate_hourly_rate()

    def test_is_profitable_active_session(self):
        """Test checking if active session is profitable."""
        session = self.create_test_session_with_hands()

        # Session has positive hand results
        assert session.is_profitable()

    def test_is_profitable_losing_session(self):
        """Test checking if session is not profitable."""
        session = PokerSession(
            session_id=SessionId.generate(),
            player_id=PlayerId(str(SessionId.generate().value)),
            game_id=GameId("ABCDE"),
            buy_in_amount=Money("100.00"),
            session_type="cash_game",
        )

        # Add losing hands
        session.add_hand(Hand(1, Money("50.00"), Money.zero()))
        session.add_hand(Hand(2, Money("75.00"), Money.zero()))

        assert not session.is_profitable()

    def test_get_session_stats(self):
        """Test getting session statistics."""
        session = self.create_test_session_with_hands()

        stats = session.get_session_stats()

        assert stats.total_hands == 3
        assert stats.winning_hands == 2  # Hands 1 and 3 are wins
        assert stats.break_even_hands == 1  # Hand 2 is break even
        assert stats.total_pot_value == Money("185.00")  # 50 + 75 + 60

    def test_get_duration(self):
        """Test getting session duration."""
        created_at = datetime(2023, 1, 1, 10, 0, 0)
        session = PokerSession(
            session_id=SessionId.generate(),
            player_id=PlayerId(str(SessionId.generate().value)),
            game_id=GameId("ABCDE"),
            buy_in_amount=Money("100.00"),
            session_type="cash_game",
            created_at=created_at,
        )

        # Mock current time to 2.5 hours later
        session._ended_at = created_at + timedelta(hours=2, minutes=30)
        session._state = SessionState.ENDED

        duration = session.get_duration()
        assert duration.minutes == 150  # 2.5 hours = 150 minutes


class TestPokerSessionAutoExpiry:
    """Test cases for session auto-expiry functionality."""

    def test_auto_end_expired_session(self):
        """Test that expired session can be auto-ended."""
        # Create session with normal time first
        session = PokerSession(
            session_id=SessionId.generate(),
            player_id=PlayerId(str(SessionId.generate().value)),
            game_id=GameId("ABCDE"),
            buy_in_amount=Money("100.00"),
            session_type="cash_game",
        )

        # Add some profit while session is active
        session.add_hand(Hand(1, Money("50.00"), Money("25.00")))
        session.clear_events()

        # Now modify creation time to make it expired (over 24 hours ago)
        old_time = datetime.utcnow() - timedelta(hours=25)
        session._created_at = old_time

        # Auto-end should work
        was_ended = session.auto_end_if_expired()

        assert was_ended
        assert session.is_expired()
        assert session.cash_out_amount == Money("125.00")  # buy_in + profit

        # Should generate auto-end event
        events = session.domain_events
        auto_end_events = [e for e in events if isinstance(e, SessionAutoEndedEvent)]
        assert len(auto_end_events) == 1

    def test_auto_end_non_expired_session(self):
        """Test that non-expired session is not auto-ended."""
        session = PokerSession(
            session_id=SessionId.generate(),
            player_id=PlayerId(str(SessionId.generate().value)),
            game_id=GameId("ABCDE"),
            buy_in_amount=Money("100.00"),
            session_type="cash_game",
        )

        was_ended = session.auto_end_if_expired()

        assert not was_ended
        assert session.is_active()

    def test_check_marathon_session_event(self):
        """Test that marathon session event is generated."""
        # Create session over 12 hours ago
        old_time = datetime.utcnow() - timedelta(hours=13)
        session = PokerSession(
            session_id=SessionId.generate(),
            player_id=PlayerId(str(SessionId.generate().value)),
            game_id=GameId("ABCDE"),
            buy_in_amount=Money("100.00"),
            session_type="cash_game",
            created_at=old_time,
        )

        session.clear_events()

        # Adding a hand should trigger marathon session check
        session.add_hand(Hand(1, Money("50.00"), Money("25.00")))

        events = session.domain_events
        marathon_events = [e for e in events if isinstance(e, MarathonSessionEvent)]
        assert len(marathon_events) == 1


class TestPokerSessionEquality:
    """Test cases for session equality and hashing."""

    def test_session_equality(self):
        """Test that sessions are equal based on session ID."""
        session_id = SessionId.generate()
        player_id = PlayerId(str(SessionId.generate().value))
        game_id = GameId("ABCDE")

        session1 = PokerSession(session_id, player_id, game_id, Money("100"), "cash")
        session2 = PokerSession(session_id, player_id, game_id, Money("200"), "tournament")

        assert session1 == session2  # Same session ID

    def test_session_inequality(self):
        """Test that sessions with different IDs are not equal."""
        player_id = PlayerId(str(SessionId.generate().value))
        game_id = GameId("ABCDE")

        session1 = PokerSession(SessionId.generate(), player_id, game_id, Money("100"), "cash")
        session2 = PokerSession(SessionId.generate(), player_id, game_id, Money("100"), "cash")

        assert session1 != session2  # Different session IDs

    def test_session_hashing(self):
        """Test that sessions can be used in sets and as dict keys."""
        session_id = SessionId.generate()
        player_id = PlayerId(str(SessionId.generate().value))
        game_id = GameId("ABCDE")

        session1 = PokerSession(session_id, player_id, game_id, Money("100"), "cash")
        session2 = PokerSession(session_id, player_id, game_id, Money("200"), "tournament")

        # Same session ID should hash to same value
        session_set = {session1, session2}
        assert len(session_set) == 1

    def test_session_string_representation(self):
        """Test session string representation."""
        session = PokerSession(
            SessionId.generate(),
            PlayerId(str(SessionId.generate().value)),
            GameId("ABCDE"),
            Money("100.00"),
            "cash_game"
        )

        repr_str = repr(session)
        assert "PokerSession" in repr_str
        assert "hands=0" in repr_str
        assert "state=active" in repr_str


if __name__ == "__main__":
    pytest.main([__file__])