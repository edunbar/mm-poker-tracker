"""
Comprehensive unit tests for ledger domain value objects.

Tests all validation rules, business logic, and methods for
LedgerEntryId, SessionReference, PlayerNames, and FinancialSummary.
"""

import pytest
from uuid import uuid4

from domain.ledger.value_objects import (
    LedgerEntryId, SessionReference, PlayerNames, FinancialSummary
)


class TestLedgerEntryId:
    """Test cases for LedgerEntryId value object."""

    def test_ledger_entry_id_creation_success(self):
        """Test successful creation of LedgerEntryId."""
        session_id = str(uuid4())
        player_id = str(uuid4())

        entry_id = LedgerEntryId(session_id=session_id, player_id=player_id)

        assert entry_id.session_id == session_id
        assert entry_id.player_id == player_id

    def test_ledger_entry_id_immutable(self):
        """Test that LedgerEntryId is immutable (frozen dataclass)."""
        entry_id = LedgerEntryId(session_id=str(uuid4()), player_id=str(uuid4()))

        with pytest.raises(AttributeError):
            entry_id.session_id = str(uuid4())

        with pytest.raises(AttributeError):
            entry_id.player_id = str(uuid4())

    def test_ledger_entry_id_empty_session_id(self):
        """Test validation fails with empty session ID."""
        with pytest.raises(ValueError, match="Session ID cannot be empty"):
            LedgerEntryId(session_id="", player_id=str(uuid4()))

    def test_ledger_entry_id_whitespace_session_id(self):
        """Test validation fails with whitespace-only session ID."""
        with pytest.raises(ValueError, match="Session ID cannot be empty"):
            LedgerEntryId(session_id="   ", player_id=str(uuid4()))

    def test_ledger_entry_id_non_string_session_id(self):
        """Test validation fails with non-string session ID."""
        with pytest.raises(ValueError, match="Session ID cannot be empty"):
            LedgerEntryId(session_id=None, player_id=str(uuid4()))

    def test_ledger_entry_id_empty_player_id(self):
        """Test validation fails with empty player ID."""
        with pytest.raises(ValueError, match="Player ID cannot be empty"):
            LedgerEntryId(session_id=str(uuid4()), player_id="")

    def test_ledger_entry_id_whitespace_player_id(self):
        """Test validation fails with whitespace-only player ID."""
        with pytest.raises(ValueError, match="Player ID cannot be empty"):
            LedgerEntryId(session_id=str(uuid4()), player_id="   ")

    def test_ledger_entry_id_non_string_player_id(self):
        """Test validation fails with non-string player ID."""
        with pytest.raises(ValueError, match="Player ID cannot be empty"):
            LedgerEntryId(session_id=str(uuid4()), player_id=None)

    def test_ledger_entry_id_invalid_session_uuid(self):
        """Test validation fails with invalid session UUID format."""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            LedgerEntryId(session_id="not-a-uuid", player_id=str(uuid4()))

    def test_ledger_entry_id_invalid_player_uuid(self):
        """Test validation fails with invalid player UUID format."""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            LedgerEntryId(session_id=str(uuid4()), player_id="not-a-uuid")

    def test_ledger_entry_id_str_representation(self):
        """Test string representation of LedgerEntryId."""
        session_id = str(uuid4())
        player_id = str(uuid4())
        entry_id = LedgerEntryId(session_id=session_id, player_id=player_id)

        assert str(entry_id) == f"{session_id}:{player_id}"

    def test_ledger_entry_id_equality(self):
        """Test equality comparison between LedgerEntryId instances."""
        session_id = str(uuid4())
        player_id = str(uuid4())

        entry_id_1 = LedgerEntryId(session_id=session_id, player_id=player_id)
        entry_id_2 = LedgerEntryId(session_id=session_id, player_id=player_id)
        entry_id_3 = LedgerEntryId(session_id=str(uuid4()), player_id=player_id)

        assert entry_id_1 == entry_id_2
        assert entry_id_1 != entry_id_3

    def test_ledger_entry_id_hashable(self):
        """Test that LedgerEntryId can be used as dictionary key or in sets."""
        entry_id_1 = LedgerEntryId(session_id=str(uuid4()), player_id=str(uuid4()))
        entry_id_2 = LedgerEntryId(session_id=str(uuid4()), player_id=str(uuid4()))

        # Should be hashable and usable in set/dict
        entry_set = {entry_id_1, entry_id_2}
        assert len(entry_set) == 2

        entry_dict = {entry_id_1: "value1", entry_id_2: "value2"}
        assert len(entry_dict) == 2


class TestSessionReference:
    """Test cases for SessionReference value object."""

    def test_session_reference_creation_success(self):
        """Test successful creation of SessionReference."""
        session_id = str(uuid4())
        external_id = "poker-now-session-123"
        game_number = 5

        session_ref = SessionReference(
            session_id=session_id,
            external_id=external_id,
            game_number=game_number
        )

        assert session_ref.session_id == session_id
        assert session_ref.external_id == external_id
        assert session_ref.game_number == game_number

    def test_session_reference_immutable(self):
        """Test that SessionReference is immutable (frozen dataclass)."""
        session_ref = SessionReference(
            session_id=str(uuid4()),
            external_id="test-session",
            game_number=1
        )

        with pytest.raises(AttributeError):
            session_ref.session_id = str(uuid4())

        with pytest.raises(AttributeError):
            session_ref.external_id = "new-external-id"

        with pytest.raises(AttributeError):
            session_ref.game_number = 2

    def test_session_reference_empty_session_id(self):
        """Test validation fails with empty session ID."""
        with pytest.raises(ValueError, match="Session ID cannot be empty"):
            SessionReference(session_id="", external_id="test", game_number=1)

    def test_session_reference_whitespace_session_id(self):
        """Test validation fails with whitespace-only session ID."""
        with pytest.raises(ValueError, match="Session ID cannot be empty"):
            SessionReference(session_id="   ", external_id="test", game_number=1)

    def test_session_reference_non_string_session_id(self):
        """Test validation fails with non-string session ID."""
        with pytest.raises(ValueError, match="Session ID cannot be empty"):
            SessionReference(session_id=None, external_id="test", game_number=1)

    def test_session_reference_empty_external_id(self):
        """Test validation fails with empty external ID."""
        with pytest.raises(ValueError, match="External ID cannot be empty"):
            SessionReference(session_id=str(uuid4()), external_id="", game_number=1)

    def test_session_reference_whitespace_external_id(self):
        """Test validation fails with whitespace-only external ID."""
        with pytest.raises(ValueError, match="External ID cannot be empty"):
            SessionReference(session_id=str(uuid4()), external_id="   ", game_number=1)

    def test_session_reference_non_string_external_id(self):
        """Test validation fails with non-string external ID."""
        with pytest.raises(ValueError, match="External ID cannot be empty"):
            SessionReference(session_id=str(uuid4()), external_id=None, game_number=1)

    def test_session_reference_zero_game_number(self):
        """Test validation fails with zero game number."""
        with pytest.raises(ValueError, match="Game number must be a positive integer"):
            SessionReference(session_id=str(uuid4()), external_id="test", game_number=0)

    def test_session_reference_negative_game_number(self):
        """Test validation fails with negative game number."""
        with pytest.raises(ValueError, match="Game number must be a positive integer"):
            SessionReference(session_id=str(uuid4()), external_id="test", game_number=-1)

    def test_session_reference_non_integer_game_number(self):
        """Test validation fails with non-integer game number."""
        with pytest.raises(ValueError, match="Game number must be a positive integer"):
            SessionReference(session_id=str(uuid4()), external_id="test", game_number=1.5)

    def test_session_reference_invalid_session_uuid(self):
        """Test validation fails with invalid session UUID format."""
        with pytest.raises(ValueError, match="Invalid session ID UUID format"):
            SessionReference(
                session_id="not-a-uuid",
                external_id="test-session",
                game_number=1
            )

    def test_session_reference_str_representation(self):
        """Test string representation of SessionReference."""
        session_ref = SessionReference(
            session_id=str(uuid4()),
            external_id="poker-session-456",
            game_number=7
        )

        assert str(session_ref) == "Session 7 (poker-session-456)"


class TestPlayerNames:
    """Test cases for PlayerNames value object."""

    def test_player_names_creation_success(self):
        """Test successful creation of PlayerNames."""
        display_name = "John Doe"
        session_names = ["John", "Johnny", "JD"]

        player_names = PlayerNames(
            display_name=display_name,
            session_names=session_names
        )

        assert player_names.display_name == display_name
        assert player_names.session_names == session_names

    def test_player_names_immutable(self):
        """Test that PlayerNames is immutable (frozen dataclass)."""
        player_names = PlayerNames(
            display_name="Alice Smith",
            session_names=["Alice"]
        )

        with pytest.raises(AttributeError):
            player_names.display_name = "Bob Wilson"

        with pytest.raises(AttributeError):
            player_names.session_names = ["Bob"]

    def test_player_names_empty_display_name(self):
        """Test validation fails with empty display name."""
        with pytest.raises(ValueError, match="Display name cannot be empty"):
            PlayerNames(display_name="", session_names=["Test"])

    def test_player_names_whitespace_display_name(self):
        """Test validation fails with whitespace-only display name."""
        with pytest.raises(ValueError, match="Display name cannot be empty"):
            PlayerNames(display_name="   ", session_names=["Test"])

    def test_player_names_non_string_display_name(self):
        """Test validation fails with non-string display name."""
        with pytest.raises(ValueError, match="Display name cannot be empty"):
            PlayerNames(display_name=None, session_names=["Test"])

    def test_player_names_non_list_session_names(self):
        """Test validation fails with non-list session names."""
        with pytest.raises(ValueError, match="Session names must be a list"):
            PlayerNames(display_name="Test", session_names="not-a-list")

    def test_player_names_empty_session_names_list(self):
        """Test validation fails with empty session names list."""
        with pytest.raises(ValueError, match="Session names list cannot be empty"):
            PlayerNames(display_name="Test", session_names=[])

    def test_player_names_empty_string_in_session_names(self):
        """Test validation fails with empty string in session names."""
        with pytest.raises(ValueError, match="All session names must be non-empty strings"):
            PlayerNames(display_name="Test", session_names=["Valid", ""])

    def test_player_names_whitespace_string_in_session_names(self):
        """Test validation fails with whitespace-only string in session names."""
        with pytest.raises(ValueError, match="All session names must be non-empty strings"):
            PlayerNames(display_name="Test", session_names=["Valid", "   "])

    def test_player_names_non_string_in_session_names(self):
        """Test validation fails with non-string in session names."""
        with pytest.raises(ValueError, match="All session names must be non-empty strings"):
            PlayerNames(display_name="Test", session_names=["Valid", None])

    def test_get_primary_session_name(self):
        """Test get_primary_session_name returns first name."""
        player_names = PlayerNames(
            display_name="Charlie Brown",
            session_names=["Charlie", "Chuck", "CB"]
        )

        assert player_names.get_primary_session_name() == "Charlie"

    def test_has_multiple_names_true(self):
        """Test has_multiple_names returns True for multiple names."""
        player_names = PlayerNames(
            display_name="David Wilson",
            session_names=["David", "Dave", "DW"]
        )

        assert player_names.has_multiple_names() is True

    def test_has_multiple_names_false(self):
        """Test has_multiple_names returns False for single name."""
        player_names = PlayerNames(
            display_name="Eve Johnson",
            session_names=["Eve"]
        )

        assert player_names.has_multiple_names() is False

    def test_contains_name_true(self):
        """Test contains_name returns True when name exists."""
        player_names = PlayerNames(
            display_name="Frank Miller",
            session_names=["Frank", "Frankie", "FM"]
        )

        assert player_names.contains_name("Frank") is True
        assert player_names.contains_name("Frankie") is True
        assert player_names.contains_name("FM") is True

    def test_contains_name_false(self):
        """Test contains_name returns False when name doesn't exist."""
        player_names = PlayerNames(
            display_name="Grace Taylor",
            session_names=["Grace", "Gracie"]
        )

        assert player_names.contains_name("Gina") is False
        assert player_names.contains_name("GT") is False

    def test_str_representation_single_name(self):
        """Test string representation with single session name."""
        player_names = PlayerNames(
            display_name="Henry Adams",
            session_names=["Henry"]
        )

        assert str(player_names) == "Henry Adams (as Henry)"

    def test_str_representation_multiple_names(self):
        """Test string representation with multiple session names."""
        player_names = PlayerNames(
            display_name="Irene Clark",
            session_names=["Irene", "Ire", "IC"]
        )

        assert str(player_names) == "Irene Clark (as Irene, Ire, IC)"


class TestFinancialSummary:
    """Test cases for FinancialSummary value object."""

    def test_financial_summary_creation_success(self):
        """Test successful creation of FinancialSummary."""
        buy_in_sum = 10000  # $100.00
        cash_out_sum = 12000  # $120.00
        in_game = 500  # $5.00
        net = 2500  # $25.00 (12000 + 500 - 10000)

        summary = FinancialSummary(
            buy_in_sum=buy_in_sum,
            cash_out_sum=cash_out_sum,
            in_game=in_game,
            net=net
        )

        assert summary.buy_in_sum == buy_in_sum
        assert summary.cash_out_sum == cash_out_sum
        assert summary.in_game == in_game
        assert summary.net == net

    def test_financial_summary_immutable(self):
        """Test that FinancialSummary is immutable (frozen dataclass)."""
        summary = FinancialSummary(
            buy_in_sum=5000,
            cash_out_sum=6000,
            in_game=0,
            net=1000
        )

        with pytest.raises(AttributeError):
            summary.buy_in_sum = 7000

        with pytest.raises(AttributeError):
            summary.cash_out_sum = 8000

        with pytest.raises(AttributeError):
            summary.in_game = 500

        with pytest.raises(AttributeError):
            summary.net = 1500

    def test_financial_summary_non_integer_buy_in(self):
        """Test validation fails with non-integer buy_in_sum."""
        with pytest.raises(TypeError, match="buy_in_sum must be an integer"):
            FinancialSummary(
                buy_in_sum=100.5,
                cash_out_sum=0,
                in_game=0,
                net=-100
            )

    def test_financial_summary_non_integer_cash_out(self):
        """Test validation fails with non-integer cash_out_sum."""
        with pytest.raises(TypeError, match="cash_out_sum must be an integer"):
            FinancialSummary(
                buy_in_sum=1000,
                cash_out_sum=50.5,
                in_game=0,
                net=-950
            )

    def test_financial_summary_non_integer_in_game(self):
        """Test validation fails with non-integer in_game."""
        with pytest.raises(TypeError, match="in_game must be an integer"):
            FinancialSummary(
                buy_in_sum=1000,
                cash_out_sum=0,
                in_game=25.5,
                net=-975
            )

    def test_financial_summary_non_integer_net(self):
        """Test validation fails with non-integer net."""
        with pytest.raises(TypeError, match="net must be an integer"):
            FinancialSummary(
                buy_in_sum=1000,
                cash_out_sum=0,
                in_game=0,
                net=-1000.5
            )

    def test_financial_summary_invalid_net_calculation(self):
        """Test validation fails when net doesn't match calculated value."""
        with pytest.raises(ValueError, match="Net amount .+ does not match calculated value"):
            FinancialSummary(
                buy_in_sum=10000,
                cash_out_sum=12000,
                in_game=500,
                net=1000  # Wrong! Should be 2500 (12000 + 500 - 10000)
            )

    def test_create_factory_method_success(self):
        """Test FinancialSummary.create factory method."""
        summary = FinancialSummary.create(
            buy_in_sum=8000,
            cash_out_sum=9500,
            in_game=200
        )

        assert summary.buy_in_sum == 8000
        assert summary.cash_out_sum == 9500
        assert summary.in_game == 200
        assert summary.net == 1700  # 9500 + 200 - 8000

    def test_create_factory_method_negative_net(self):
        """Test FinancialSummary.create with losing session."""
        summary = FinancialSummary.create(
            buy_in_sum=10000,
            cash_out_sum=5000,
            in_game=0
        )

        assert summary.net == -5000  # 5000 + 0 - 10000

    def test_create_factory_method_zero_net(self):
        """Test FinancialSummary.create with break-even session."""
        summary = FinancialSummary.create(
            buy_in_sum=10000,
            cash_out_sum=7000,
            in_game=3000
        )

        assert summary.net == 0  # 7000 + 3000 - 10000

    def test_to_dollars_conversion(self):
        """Test to_dollars converts cents to dollar values."""
        summary = FinancialSummary.create(
            buy_in_sum=12500,  # $125.00
            cash_out_sum=15750,  # $157.50
            in_game=250  # $2.50
        )

        dollars = summary.to_dollars()

        expected = {
            "buy_in_sum": 125.0,
            "cash_out_sum": 157.5,
            "in_game": 2.5,
            "net": 35.0  # (15750 + 250 - 12500) / 100
        }

        assert dollars == expected

    def test_is_profitable_true(self):
        """Test is_profitable returns True for positive net."""
        summary = FinancialSummary.create(
            buy_in_sum=5000,
            cash_out_sum=7000,
            in_game=0
        )

        assert summary.is_profitable() is True

    def test_is_profitable_false_negative(self):
        """Test is_profitable returns False for negative net."""
        summary = FinancialSummary.create(
            buy_in_sum=10000,
            cash_out_sum=6000,
            in_game=0
        )

        assert summary.is_profitable() is False

    def test_is_profitable_false_zero(self):
        """Test is_profitable returns False for zero net."""
        summary = FinancialSummary.create(
            buy_in_sum=5000,
            cash_out_sum=3000,
            in_game=2000
        )

        assert summary.is_profitable() is False

    def test_is_break_even_true(self):
        """Test is_break_even returns True for zero net."""
        summary = FinancialSummary.create(
            buy_in_sum=8000,
            cash_out_sum=5000,
            in_game=3000
        )

        assert summary.is_break_even() is True

    def test_is_break_even_false_positive(self):
        """Test is_break_even returns False for positive net."""
        summary = FinancialSummary.create(
            buy_in_sum=5000,
            cash_out_sum=6000,
            in_game=0
        )

        assert summary.is_break_even() is False

    def test_is_break_even_false_negative(self):
        """Test is_break_even returns False for negative net."""
        summary = FinancialSummary.create(
            buy_in_sum=10000,
            cash_out_sum=7000,
            in_game=0
        )

        assert summary.is_break_even() is False

    def test_is_losing_true(self):
        """Test is_losing returns True for negative net."""
        summary = FinancialSummary.create(
            buy_in_sum=15000,
            cash_out_sum=8000,
            in_game=2000
        )

        assert summary.is_losing() is True

    def test_is_losing_false_positive(self):
        """Test is_losing returns False for positive net."""
        summary = FinancialSummary.create(
            buy_in_sum=5000,
            cash_out_sum=8000,
            in_game=0
        )

        assert summary.is_losing() is False

    def test_is_losing_false_zero(self):
        """Test is_losing returns False for zero net."""
        summary = FinancialSummary.create(
            buy_in_sum=6000,
            cash_out_sum=4000,
            in_game=2000
        )

        assert summary.is_losing() is False

    def test_with_updated_amounts_partial_update(self):
        """Test with_updated_amounts with partial parameter updates."""
        original = FinancialSummary.create(
            buy_in_sum=5000,
            cash_out_sum=6000,
            in_game=500
        )

        # Update only buy_in_sum
        updated = original.with_updated_amounts(buy_in_sum=7000)

        assert updated.buy_in_sum == 7000
        assert updated.cash_out_sum == 6000  # Unchanged
        assert updated.in_game == 500  # Unchanged
        assert updated.net == -500  # Recalculated: 6000 + 500 - 7000

    def test_with_updated_amounts_all_fields(self):
        """Test with_updated_amounts with all parameters updated."""
        original = FinancialSummary.create(
            buy_in_sum=10000,
            cash_out_sum=8000,
            in_game=1000
        )

        updated = original.with_updated_amounts(
            buy_in_sum=12000,
            cash_out_sum=15000,
            in_game=2000
        )

        assert updated.buy_in_sum == 12000
        assert updated.cash_out_sum == 15000
        assert updated.in_game == 2000
        assert updated.net == 5000  # 15000 + 2000 - 12000

    def test_with_updated_amounts_no_parameters(self):
        """Test with_updated_amounts with no parameters returns equivalent instance."""
        original = FinancialSummary.create(
            buy_in_sum=3000,
            cash_out_sum=4000,
            in_game=500
        )

        updated = original.with_updated_amounts()

        assert updated.buy_in_sum == original.buy_in_sum
        assert updated.cash_out_sum == original.cash_out_sum
        assert updated.in_game == original.in_game
        assert updated.net == original.net

    def test_financial_summary_edge_cases(self):
        """Test edge cases with zero and negative values."""
        # All zeros
        zero_summary = FinancialSummary.create(
            buy_in_sum=0,
            cash_out_sum=0,
            in_game=0
        )
        assert zero_summary.net == 0
        assert zero_summary.is_break_even() is True

        # Negative cash_out (unusual but mathematically valid)
        negative_cash_out = FinancialSummary.create(
            buy_in_sum=1000,
            cash_out_sum=-500,  # Unusual case
            in_game=0
        )
        assert negative_cash_out.net == -1500  # -500 + 0 - 1000

    def test_financial_summary_large_values(self):
        """Test with large monetary values."""
        # $1 million buy-in scenario
        large_summary = FinancialSummary.create(
            buy_in_sum=100_000_000,  # $1,000,000
            cash_out_sum=120_000_000,  # $1,200,000
            in_game=5_000_000  # $50,000
        )

        assert large_summary.net == 25_000_000  # $250,000 profit
        assert large_summary.is_profitable() is True

        dollars = large_summary.to_dollars()
        assert dollars["net"] == 250_000.0