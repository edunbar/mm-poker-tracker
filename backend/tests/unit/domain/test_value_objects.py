"""
Unit tests for poker domain value objects.

These tests ensure that value objects behave correctly, including:
- Immutability
- Validation rules
- Mathematical operations
- Equality and hashing
"""

import pytest
from decimal import Decimal
from uuid import uuid4

from domain.poker.value_objects import (
    Money,
    SessionId,
    PlayerId,
    GameId,
    Hand,
    SessionDuration,
    SessionStats,
)


class TestMoney:
    """Test cases for Money value object."""

    def test_create_money_from_various_types(self):
        """Test creating Money from different input types."""
        # Test string input
        money_str = Money("100.50")
        assert money_str.amount == Decimal("100.50")

        # Test int input
        money_int = Money(100)
        assert money_int.amount == Decimal("100.00")

        # Test float input
        money_float = Money(100.75)
        assert money_float.amount == Decimal("100.75")

        # Test Decimal input
        money_decimal = Money(Decimal("100.33"))
        assert money_decimal.amount == Decimal("100.33")

    def test_money_precision_rounding(self):
        """Test that Money correctly rounds to 2 decimal places."""
        money = Money("100.999")
        assert money.amount == Decimal("101.00")

        money = Money("100.994")
        assert money.amount == Decimal("100.99")

    def test_money_negative_amounts_allowed(self):
        """Test that Money allows negative amounts for balance scenarios."""
        # Negative amounts are now allowed for debt/balance calculations
        negative_money = Money(-10.50)
        assert negative_money.amount == Decimal("-10.50")
        assert str(negative_money) == "$-10.50"

        # Test that negative amounts work in calculations
        positive_money = Money("20.00")
        result = positive_money + negative_money
        assert result.amount == Decimal("9.50")

    def test_money_invalid_input(self):
        """Test that Money rejects invalid inputs."""
        with pytest.raises(ValueError, match="Invalid monetary amount"):
            Money("not a number")

        with pytest.raises(ValueError, match="Invalid monetary amount"):
            Money(None)

    def test_money_zero_factory(self):
        """Test Money.zero() factory method."""
        zero = Money.zero()
        assert zero.amount == Decimal("0.00")
        assert zero.is_zero()

    def test_money_addition(self):
        """Test Money addition operations."""
        money1 = Money("100.50")
        money2 = Money("50.25")
        result = money1 + money2

        assert result.amount == Decimal("150.75")
        assert isinstance(result, Money)

        # Test adding zero
        zero_result = money1 + Money.zero()
        assert zero_result.amount == money1.amount

    def test_money_addition_type_error(self):
        """Test that Money addition with non-Money raises TypeError."""
        money = Money("100.00")
        with pytest.raises(TypeError, match="Can only add Money to Money"):
            money + 50

    def test_money_subtraction(self):
        """Test Money subtraction operations."""
        money1 = Money("100.50")
        money2 = Money("50.25")
        result = money1 - money2

        assert result.amount == Decimal("50.25")

    def test_money_subtraction_negative_result(self):
        """Test that subtraction can result in negative amounts for balance calculations."""
        money1 = Money("50.00")
        money2 = Money("100.00")

        # Subtraction now allows negative results for debt/balance scenarios
        result = money1 - money2
        assert result.amount == Decimal("-50.00")
        assert str(result) == "$-50.00"

        # Test the inverse
        result2 = money2 - money1
        assert result2.amount == Decimal("50.00")

    def test_money_multiplication(self):
        """Test Money multiplication operations."""
        money = Money("100.00")

        # Test with int
        result_int = money * 2
        assert result_int.amount == Decimal("200.00")

        # Test with float
        result_float = money * 1.5
        assert result_float.amount == Decimal("150.00")

        # Test with Decimal
        result_decimal = money * Decimal("0.5")
        assert result_decimal.amount == Decimal("50.00")

    def test_money_division(self):
        """Test Money division operations."""
        money = Money("100.00")

        result = money / 4
        assert result.amount == Decimal("25.00")

        result_float = money / 2.5
        assert result_float.amount == Decimal("40.00")

    def test_money_division_by_zero(self):
        """Test that division by zero raises error."""
        money = Money("100.00")
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            money / 0

    def test_money_comparison_operations(self):
        """Test Money comparison operations."""
        money1 = Money("100.00")
        money2 = Money("50.00")
        money3 = Money("100.00")

        # Test equality
        assert money1 == money3
        assert money1 != money2

        # Test ordering
        assert money1 > money2
        assert money2 < money1
        assert money1 >= money3
        assert money1 <= money3

    def test_money_comparison_type_error(self):
        """Test that comparing Money with non-Money raises TypeError."""
        money = Money("100.00")
        with pytest.raises(TypeError):
            money < 50

    def test_money_hashing(self):
        """Test that Money is hashable and works in sets/dicts."""
        money1 = Money("100.00")
        money2 = Money("100.00")
        money3 = Money("50.00")

        money_set = {money1, money2, money3}
        assert len(money_set) == 2  # money1 and money2 should be the same

        money_dict = {money1: "hundred", money3: "fifty"}
        assert money_dict[money2] == "hundred"

    def test_money_string_representation(self):
        """Test Money string representations."""
        money = Money("100.50")
        assert str(money) == "$100.50"
        assert repr(money) == "Money(100.50)"

    def test_money_utility_methods(self):
        """Test Money utility methods."""
        positive = Money("100.00")
        zero = Money.zero()

        assert positive.is_positive()
        assert not zero.is_positive()

        assert zero.is_zero()
        assert not positive.is_zero()

    def test_money_to_float_conversion(self):
        """Test Money to float conversion (for legacy compatibility)."""
        money = Money("100.50")
        assert money.to_float() == 100.50


class TestSessionId:
    """Test cases for SessionId value object."""

    def test_create_session_id_with_valid_uuid(self):
        """Test creating SessionId with valid UUID."""
        uuid_str = str(uuid4())
        session_id = SessionId(uuid_str)
        assert session_id.value == uuid_str

    def test_session_id_invalid_uuid(self):
        """Test that SessionId rejects invalid UUIDs."""
        with pytest.raises(ValueError, match="Session ID must be a valid UUID"):
            SessionId("not-a-uuid")

    def test_session_id_empty_string(self):
        """Test that SessionId rejects empty string."""
        with pytest.raises(ValueError, match="Session ID cannot be empty"):
            SessionId("")

    def test_session_id_generate(self):
        """Test SessionId.generate() factory method."""
        session_id = SessionId.generate()
        assert isinstance(session_id, SessionId)
        # Should be able to create UUID from the value
        from uuid import UUID
        UUID(session_id.value)  # This will raise ValueError if invalid

    def test_session_id_string_conversion(self):
        """Test SessionId string conversion."""
        uuid_str = str(uuid4())
        session_id = SessionId(uuid_str)
        assert str(session_id) == uuid_str

    def test_session_id_immutability(self):
        """Test that SessionId is immutable."""
        session_id = SessionId(str(uuid4()))
        with pytest.raises(AttributeError):
            session_id.value = "new-value"


class TestPlayerId:
    """Test cases for PlayerId value object."""

    def test_create_player_id_with_valid_uuid(self):
        """Test creating PlayerId with valid UUID."""
        uuid_str = str(uuid4())
        player_id = PlayerId(uuid_str)
        assert player_id.value == uuid_str

    def test_player_id_invalid_uuid(self):
        """Test that PlayerId rejects invalid UUIDs."""
        with pytest.raises(ValueError, match="Player ID must be a valid UUID"):
            PlayerId("invalid-uuid")

    def test_player_id_empty_string(self):
        """Test that PlayerId rejects empty string."""
        with pytest.raises(ValueError, match="Player ID cannot be empty"):
            PlayerId("")


class TestGameId:
    """Test cases for GameId value object."""

    def test_create_game_id_with_valid_format(self):
        """Test creating GameId with valid 5-character format."""
        game_id = GameId("ABCDE")
        assert game_id.value == "ABCDE"

    def test_game_id_invalid_length(self):
        """Test that GameId rejects invalid lengths."""
        with pytest.raises(ValueError, match="Game ID must be either 5 characters \\(public code\\) or 36 characters \\(UUID\\)"):
            GameId("ABC")

        with pytest.raises(ValueError, match="Game ID must be either 5 characters \\(public code\\) or 36 characters \\(UUID\\)"):
            GameId("ABCDEF")

    def test_game_id_empty_string(self):
        """Test that GameId rejects empty string."""
        with pytest.raises(ValueError, match="Game ID cannot be empty"):
            GameId("")


class TestHand:
    """Test cases for Hand value object."""

    def test_create_hand_with_valid_data(self):
        """Test creating Hand with valid data."""
        hand = Hand(
            hand_number=1,
            pot_size=Money("100.00"),
            player_result=Money("50.00")
        )

        assert hand.hand_number == 1
        assert hand.pot_size == Money("100.00")
        assert hand.player_result == Money("50.00")

    def test_hand_invalid_hand_number(self):
        """Test that Hand rejects invalid hand numbers."""
        with pytest.raises(ValueError, match="Hand number must be positive"):
            Hand(
                hand_number=0,
                pot_size=Money("100.00"),
                player_result=Money("50.00")
            )

    def test_hand_invalid_types(self):
        """Test that Hand validates parameter types."""
        with pytest.raises(TypeError, match="pot_size must be a Money instance"):
            Hand(
                hand_number=1,
                pot_size=100.00,  # Not a Money instance
                player_result=Money("50.00")
            )

        with pytest.raises(TypeError, match="player_result must be a Money instance"):
            Hand(
                hand_number=1,
                pot_size=Money("100.00"),
                player_result=50.00  # Not a Money instance
            )

    def test_hand_utility_methods(self):
        """Test Hand utility methods."""
        winning_hand = Hand(
            hand_number=1,
            pot_size=Money("100.00"),
            player_result=Money("50.00")
        )

        break_even_hand = Hand(
            hand_number=2,
            pot_size=Money("100.00"),
            player_result=Money.zero()
        )

        assert winning_hand.is_winning_hand()
        assert not winning_hand.is_break_even_hand()

        assert not break_even_hand.is_winning_hand()
        assert break_even_hand.is_break_even_hand()


class TestSessionDuration:
    """Test cases for SessionDuration value object."""

    def test_create_session_duration(self):
        """Test creating SessionDuration."""
        duration = SessionDuration(120)  # 2 hours
        assert duration.minutes == 120

    def test_session_duration_negative_validation(self):
        """Test that SessionDuration rejects negative minutes."""
        with pytest.raises(ValueError, match="Session duration cannot be negative"):
            SessionDuration(-30)

    def test_session_duration_from_hours(self):
        """Test creating SessionDuration from hours."""
        duration = SessionDuration.from_hours(2.5)
        assert duration.minutes == 150

        with pytest.raises(ValueError, match="Hours cannot be negative"):
            SessionDuration.from_hours(-1)

    def test_session_duration_to_hours(self):
        """Test converting SessionDuration to hours."""
        duration = SessionDuration(90)
        assert duration.to_hours() == 1.5

    def test_session_duration_marathon_check(self):
        """Test marathon session detection."""
        normal_session = SessionDuration(600)  # 10 hours
        marathon_session = SessionDuration(800)  # 13+ hours

        assert not normal_session.is_marathon_session()
        assert marathon_session.is_marathon_session()

    def test_session_duration_string_representation(self):
        """Test SessionDuration string representation."""
        duration_with_hours = SessionDuration(90)  # 1h 30m
        assert str(duration_with_hours) == "1h 30m"

        duration_minutes_only = SessionDuration(45)  # 45m
        assert str(duration_minutes_only) == "45m"


class TestSessionStats:
    """Test cases for SessionStats value object."""

    def test_create_session_stats(self):
        """Test creating SessionStats with valid data."""
        stats = SessionStats(
            total_hands=100,
            winning_hands=30,
            break_even_hands=20,
            total_pot_value=Money("5000.00")
        )

        assert stats.total_hands == 100
        assert stats.winning_hands == 30
        assert stats.break_even_hands == 20
        assert stats.total_pot_value == Money("5000.00")

    def test_session_stats_validation(self):
        """Test SessionStats validation rules."""
        # Negative values
        with pytest.raises(ValueError, match="Total hands cannot be negative"):
            SessionStats(-1, 10, 5, Money("1000.00"))

        with pytest.raises(ValueError, match="Winning hands cannot be negative"):
            SessionStats(100, -1, 5, Money("1000.00"))

        with pytest.raises(ValueError, match="Break-even hands cannot be negative"):
            SessionStats(100, 10, -1, Money("1000.00"))

        # Winning + break-even > total
        with pytest.raises(ValueError, match="Winning \\+ break-even hands cannot exceed total hands"):
            SessionStats(100, 60, 50, Money("1000.00"))  # 110 > 100

    def test_session_stats_calculated_properties(self):
        """Test SessionStats calculated properties."""
        stats = SessionStats(
            total_hands=100,
            winning_hands=30,
            break_even_hands=20,
            total_pot_value=Money("5000.00")
        )

        assert stats.losing_hands == 50  # 100 - 30 - 20
        assert stats.win_rate() == 30.0  # 30/100 * 100
        assert stats.break_even_rate() == 20.0  # 20/100 * 100

    def test_session_stats_zero_hands(self):
        """Test SessionStats with zero hands."""
        stats = SessionStats(
            total_hands=0,
            winning_hands=0,
            break_even_hands=0,
            total_pot_value=Money.zero()
        )

        assert stats.losing_hands == 0
        assert stats.win_rate() == 0.0
        assert stats.break_even_rate() == 0.0


if __name__ == "__main__":
    pytest.main([__file__])