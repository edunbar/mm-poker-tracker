"""
Comprehensive unit tests for ledger domain entities.

Tests all business logic, validation rules, and domain operations
for LedgerEntry and SessionLedger entities.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from domain.poker.value_objects import GameId
from domain.ledger.entities import LedgerEntry, SessionLedger
from domain.ledger.value_objects import (
    LedgerEntryId, SessionReference, PlayerNames, FinancialSummary
)


class TestLedgerEntry:
    """Test cases for LedgerEntry entity."""

    @pytest.fixture
    def sample_game_id(self):
        return GameId(str(uuid4()))

    @pytest.fixture
    def sample_ledger_entry_id(self):
        return LedgerEntryId(
            session_id=str(uuid4()),
            player_id=str(uuid4())
        )

    @pytest.fixture
    def sample_session_reference(self, sample_ledger_entry_id):
        return SessionReference(
            session_id=sample_ledger_entry_id.session_id,
            external_id="test-session-123",
            game_number=5
        )

    @pytest.fixture
    def sample_player_names(self):
        return PlayerNames(
            display_name="John Doe",
            session_names=["John", "Johnny"]
        )

    @pytest.fixture
    def sample_financial_summary(self):
        return FinancialSummary.create(
            buy_in_sum=10000,  # $100.00
            cash_out_sum=15000,  # $150.00
            in_game=0
        )

    @pytest.fixture
    def sample_ledger_entry(self, sample_ledger_entry_id, sample_game_id,
                          sample_session_reference, sample_player_names,
                          sample_financial_summary):
        return LedgerEntry(
            id=sample_ledger_entry_id,
            game_id=sample_game_id,
            session_reference=sample_session_reference,
            player_names=sample_player_names,
            financial_summary=sample_financial_summary
        )

    def test_ledger_entry_creation_success(self, sample_ledger_entry):
        """Test successful creation of LedgerEntry."""
        assert sample_ledger_entry.id is not None
        assert sample_ledger_entry.game_id is not None
        assert sample_ledger_entry.session_reference is not None
        assert sample_ledger_entry.player_names is not None
        assert sample_ledger_entry.financial_summary is not None
        assert sample_ledger_entry.session_started_at is None
        assert sample_ledger_entry.session_ended_at is None
        assert sample_ledger_entry.has_csv_data is False

    def test_ledger_entry_creation_with_timestamps(self, sample_ledger_entry_id,
                                                  sample_game_id, sample_session_reference,
                                                  sample_player_names, sample_financial_summary):
        """Test LedgerEntry creation with timestamps."""
        start_time = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 1, 15, 14, 30, 0, tzinfo=timezone.utc)

        entry = LedgerEntry(
            id=sample_ledger_entry_id,
            game_id=sample_game_id,
            session_reference=sample_session_reference,
            player_names=sample_player_names,
            financial_summary=sample_financial_summary,
            session_started_at=start_time,
            session_ended_at=end_time,
            has_csv_data=True
        )

        assert entry.session_started_at == start_time
        assert entry.session_ended_at == end_time
        assert entry.has_csv_data is True

    def test_ledger_entry_invalid_id_type(self, sample_game_id, sample_session_reference,
                                        sample_player_names, sample_financial_summary):
        """Test LedgerEntry validation fails with invalid ID type."""
        with pytest.raises(TypeError, match="id must be a LedgerEntryId instance"):
            LedgerEntry(
                id="invalid-id",
                game_id=sample_game_id,
                session_reference=sample_session_reference,
                player_names=sample_player_names,
                financial_summary=sample_financial_summary
            )

    def test_ledger_entry_invalid_game_id_type(self, sample_ledger_entry_id,
                                             sample_session_reference, sample_player_names,
                                             sample_financial_summary):
        """Test LedgerEntry validation fails with invalid game_id type."""
        with pytest.raises(TypeError, match="game_id must be a GameId instance"):
            LedgerEntry(
                id=sample_ledger_entry_id,
                game_id="invalid-game-id",
                session_reference=sample_session_reference,
                player_names=sample_player_names,
                financial_summary=sample_financial_summary
            )

    def test_ledger_entry_invalid_session_reference_type(self, sample_ledger_entry_id,
                                                       sample_game_id, sample_player_names,
                                                       sample_financial_summary):
        """Test LedgerEntry validation fails with invalid session_reference type."""
        with pytest.raises(TypeError, match="session_reference must be a SessionReference instance"):
            LedgerEntry(
                id=sample_ledger_entry_id,
                game_id=sample_game_id,
                session_reference="invalid-session-ref",
                player_names=sample_player_names,
                financial_summary=sample_financial_summary
            )

    def test_ledger_entry_invalid_player_names_type(self, sample_ledger_entry_id,
                                                  sample_game_id, sample_session_reference,
                                                  sample_financial_summary):
        """Test LedgerEntry validation fails with invalid player_names type."""
        with pytest.raises(TypeError, match="player_names must be a PlayerNames instance"):
            LedgerEntry(
                id=sample_ledger_entry_id,
                game_id=sample_game_id,
                session_reference=sample_session_reference,
                player_names="invalid-names",
                financial_summary=sample_financial_summary
            )

    def test_ledger_entry_invalid_financial_summary_type(self, sample_ledger_entry_id,
                                                       sample_game_id, sample_session_reference,
                                                       sample_player_names):
        """Test LedgerEntry validation fails with invalid financial_summary type."""
        with pytest.raises(TypeError, match="financial_summary must be a FinancialSummary instance"):
            LedgerEntry(
                id=sample_ledger_entry_id,
                game_id=sample_game_id,
                session_reference=sample_session_reference,
                player_names=sample_player_names,
                financial_summary="invalid-summary"
            )

    def test_ledger_entry_session_id_consistency_check(self, sample_game_id,
                                                      sample_player_names, sample_financial_summary):
        """Test LedgerEntry validates session ID consistency between id and session_reference."""
        session_id_1 = str(uuid4())
        session_id_2 = str(uuid4())

        entry_id = LedgerEntryId(session_id=session_id_1, player_id=str(uuid4()))
        session_ref = SessionReference(
            session_id=session_id_2,  # Different session ID!
            external_id="test-session-123",
            game_number=5
        )

        with pytest.raises(ValueError, match="LedgerEntryId session_id must match SessionReference session_id"):
            LedgerEntry(
                id=entry_id,
                game_id=sample_game_id,
                session_reference=session_ref,
                player_names=sample_player_names,
                financial_summary=sample_financial_summary
            )

    def test_ledger_entry_invalid_timestamp_order(self, sample_ledger_entry_id,
                                                 sample_game_id, sample_session_reference,
                                                 sample_player_names, sample_financial_summary):
        """Test LedgerEntry validation fails when start time is after end time."""
        start_time = datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)  # Earlier than start!

        with pytest.raises(ValueError, match="Session start time cannot be after end time"):
            LedgerEntry(
                id=sample_ledger_entry_id,
                game_id=sample_game_id,
                session_reference=sample_session_reference,
                player_names=sample_player_names,
                financial_summary=sample_financial_summary,
                session_started_at=start_time,
                session_ended_at=end_time
            )

    def test_create_new_factory_method_success(self, sample_game_id):
        """Test LedgerEntry.create_new factory method."""
        session_id = str(uuid4())
        player_id = str(uuid4())

        entry = LedgerEntry.create_new(
            session_id=session_id,
            player_id=player_id,
            game_id=sample_game_id,
            external_id="test-session-456",
            game_number=7,
            display_name="Jane Smith",
            session_names=["Jane", "J"],
            buy_in_sum=5000,
            cash_out_sum=4500,
            in_game=0
        )

        assert entry.id.session_id == session_id
        assert entry.id.player_id == player_id
        assert entry.game_id == sample_game_id
        assert entry.session_reference.external_id == "test-session-456"
        assert entry.session_reference.game_number == 7
        assert entry.player_names.display_name == "Jane Smith"
        assert entry.player_names.session_names == ["Jane", "J"]
        assert entry.financial_summary.buy_in_sum == 5000
        assert entry.financial_summary.cash_out_sum == 4500
        assert entry.financial_summary.in_game == 0
        assert entry.financial_summary.net == -500  # 4500 + 0 - 5000

    def test_create_new_with_optional_params(self, sample_game_id):
        """Test LedgerEntry.create_new with optional parameters."""
        start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 1, 15, 16, 0, 0, tzinfo=timezone.utc)

        entry = LedgerEntry.create_new(
            session_id=str(uuid4()),
            player_id=str(uuid4()),
            game_id=sample_game_id,
            external_id="test-session-789",
            game_number=10,
            display_name="Bob Wilson",
            session_names=["Bob"],
            buy_in_sum=20000,
            cash_out_sum=25000,
            in_game=1000,
            session_started_at=start_time,
            session_ended_at=end_time,
            has_csv_data=True
        )

        assert entry.session_started_at == start_time
        assert entry.session_ended_at == end_time
        assert entry.has_csv_data is True

    def test_get_session_id(self, sample_ledger_entry):
        """Test get_session_id method."""
        assert sample_ledger_entry.get_session_id() == sample_ledger_entry.id.session_id

    def test_get_player_id(self, sample_ledger_entry):
        """Test get_player_id method."""
        assert sample_ledger_entry.get_player_id() == sample_ledger_entry.id.player_id

    def test_is_profitable_true(self, sample_ledger_entry):
        """Test is_profitable returns True for profitable session."""
        # sample_financial_summary has net = 5000 (positive)
        assert sample_ledger_entry.is_profitable() is True

    def test_is_profitable_false(self, sample_ledger_entry_id, sample_game_id,
                                sample_session_reference, sample_player_names):
        """Test is_profitable returns False for losing session."""
        losing_summary = FinancialSummary.create(
            buy_in_sum=10000,
            cash_out_sum=5000,
            in_game=0
        )

        entry = LedgerEntry(
            id=sample_ledger_entry_id,
            game_id=sample_game_id,
            session_reference=sample_session_reference,
            player_names=sample_player_names,
            financial_summary=losing_summary
        )

        assert entry.is_profitable() is False

    def test_is_session_ended_true(self, sample_ledger_entry_id, sample_game_id,
                                  sample_session_reference, sample_player_names,
                                  sample_financial_summary):
        """Test is_session_ended returns True when session has end time."""
        entry = LedgerEntry(
            id=sample_ledger_entry_id,
            game_id=sample_game_id,
            session_reference=sample_session_reference,
            player_names=sample_player_names,
            financial_summary=sample_financial_summary,
            session_ended_at=datetime.now(timezone.utc)
        )

        assert entry.is_session_ended() is True

    def test_is_session_ended_false(self, sample_ledger_entry):
        """Test is_session_ended returns False when session has no end time."""
        assert sample_ledger_entry.is_session_ended() is False

    def test_get_net_dollars(self, sample_ledger_entry):
        """Test get_net_dollars conversion from cents to dollars."""
        # sample_financial_summary has net = 5000 cents = $50.00
        assert sample_ledger_entry.get_net_dollars() == 50.0

    def test_update_financial_data_partial_update(self, sample_ledger_entry):
        """Test update_financial_data with partial updates."""
        updated_entry = sample_ledger_entry.update_financial_data(buy_in_sum=12000)

        # Original entry should be unchanged (immutability)
        assert sample_ledger_entry.financial_summary.buy_in_sum == 10000

        # New entry should have updated values
        assert updated_entry.financial_summary.buy_in_sum == 12000
        assert updated_entry.financial_summary.cash_out_sum == 15000  # Unchanged
        assert updated_entry.financial_summary.in_game == 0  # Unchanged
        assert updated_entry.financial_summary.net == 3000  # Recalculated: 15000 + 0 - 12000

    def test_update_financial_data_all_fields(self, sample_ledger_entry):
        """Test update_financial_data with all fields updated."""
        updated_entry = sample_ledger_entry.update_financial_data(
            buy_in_sum=8000,
            cash_out_sum=9000,
            in_game=500
        )

        assert updated_entry.financial_summary.buy_in_sum == 8000
        assert updated_entry.financial_summary.cash_out_sum == 9000
        assert updated_entry.financial_summary.in_game == 500
        assert updated_entry.financial_summary.net == 1500  # 9000 + 500 - 8000

    def test_update_player_names(self, sample_ledger_entry):
        """Test update_player_names creates new entry with updated names."""
        new_names = ["John D", "Johnny D", "JD"]
        updated_entry = sample_ledger_entry.update_player_names(new_names)

        # Original entry should be unchanged (immutability)
        assert sample_ledger_entry.player_names.session_names == ["John", "Johnny"]

        # New entry should have updated names
        assert updated_entry.player_names.session_names == new_names
        assert updated_entry.player_names.display_name == "John Doe"  # Unchanged

    def test_to_dict_complete(self, sample_ledger_entry_id, sample_game_id,
                             sample_session_reference, sample_player_names,
                             sample_financial_summary):
        """Test to_dict method with complete data including timestamps."""
        start_time = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc)

        entry = LedgerEntry(
            id=sample_ledger_entry_id,
            game_id=sample_game_id,
            session_reference=sample_session_reference,
            player_names=sample_player_names,
            financial_summary=sample_financial_summary,
            session_started_at=start_time,
            session_ended_at=end_time,
            has_csv_data=True
        )

        result = entry.to_dict()

        expected = {
            "session_id": sample_ledger_entry_id.session_id,
            "player_id": sample_ledger_entry_id.player_id,
            "player_name": "John Doe",
            "session_external_id": "test-session-123",
            "session_started_at": "2025-01-15T10:00:00+00:00",
            "session_ended_at": "2025-01-15T14:00:00+00:00",
            "buy_in_sum": 10000,
            "cash_out_sum": 15000,
            "in_game": 0,
            "net": 5000,
            "names": ["John", "Johnny"],
            "game_number": 5,
            "has_csv": True
        }

        assert result == expected

    def test_to_dict_minimal(self, sample_ledger_entry):
        """Test to_dict method with minimal data (no timestamps)."""
        result = sample_ledger_entry.to_dict()

        assert result["session_started_at"] is None
        assert result["session_ended_at"] is None
        assert result["has_csv"] is False

    def test_str_representation(self, sample_ledger_entry):
        """Test string representation of LedgerEntry."""
        str_repr = str(sample_ledger_entry)
        assert "LedgerEntry(John Doe in Session 5)" == str_repr


class TestSessionLedger:
    """Test cases for SessionLedger entity."""

    @pytest.fixture
    def sample_game_id(self):
        return GameId(str(uuid4()))

    @pytest.fixture
    def sample_session_reference(self):
        return SessionReference(
            session_id=str(uuid4()),
            external_id="test-session-999",
            game_number=3
        )

    @pytest.fixture
    def sample_ledger_entry_1(self, sample_game_id, sample_session_reference):
        return LedgerEntry.create_new(
            session_id=sample_session_reference.session_id,
            player_id=str(uuid4()),
            game_id=sample_game_id,
            external_id=sample_session_reference.external_id,
            game_number=sample_session_reference.game_number,
            display_name="Alice",
            session_names=["Alice"],
            buy_in_sum=10000,
            cash_out_sum=12000,
            in_game=0
        )

    @pytest.fixture
    def sample_ledger_entry_2(self, sample_game_id, sample_session_reference):
        return LedgerEntry.create_new(
            session_id=sample_session_reference.session_id,
            player_id=str(uuid4()),
            game_id=sample_game_id,
            external_id=sample_session_reference.external_id,
            game_number=sample_session_reference.game_number,
            display_name="Bob",
            session_names=["Bob"],
            buy_in_sum=8000,
            cash_out_sum=6000,
            in_game=500
        )

    @pytest.fixture
    def sample_session_ledger(self, sample_session_reference, sample_game_id):
        return SessionLedger(
            session_reference=sample_session_reference,
            game_id=sample_game_id
        )

    def test_session_ledger_creation_empty(self, sample_session_ledger):
        """Test SessionLedger creation with no entries."""
        assert sample_session_ledger.session_reference is not None
        assert sample_session_ledger.game_id is not None
        assert len(sample_session_ledger.entries) == 0

    def test_session_ledger_creation_with_entries(self, sample_session_reference,
                                                 sample_game_id, sample_ledger_entry_1):
        """Test SessionLedger creation with initial entries."""
        ledger = SessionLedger(
            session_reference=sample_session_reference,
            game_id=sample_game_id,
            entries=[sample_ledger_entry_1]
        )

        assert len(ledger.entries) == 1
        assert ledger.entries[0] == sample_ledger_entry_1

    def test_session_ledger_invalid_session_reference_type(self, sample_game_id):
        """Test SessionLedger validation fails with invalid session_reference type."""
        with pytest.raises(TypeError, match="session_reference must be a SessionReference instance"):
            SessionLedger(
                session_reference="invalid-ref",
                game_id=sample_game_id
            )

    def test_session_ledger_invalid_game_id_type(self, sample_session_reference):
        """Test SessionLedger validation fails with invalid game_id type."""
        with pytest.raises(TypeError, match="game_id must be a GameId instance"):
            SessionLedger(
                session_reference=sample_session_reference,
                game_id="invalid-game-id"
            )

    def test_session_ledger_invalid_entries_type(self, sample_session_reference, sample_game_id):
        """Test SessionLedger validation fails with invalid entries type."""
        with pytest.raises(TypeError, match="entries must be a list"):
            SessionLedger(
                session_reference=sample_session_reference,
                game_id=sample_game_id,
                entries="invalid-entries"
            )

    def test_session_ledger_invalid_entry_type(self, sample_session_reference, sample_game_id):
        """Test SessionLedger validation fails with invalid entry type in list."""
        with pytest.raises(TypeError, match="All entries must be LedgerEntry instances"):
            SessionLedger(
                session_reference=sample_session_reference,
                game_id=sample_game_id,
                entries=["invalid-entry"]
            )

    def test_session_ledger_mismatched_session_id(self, sample_session_reference,
                                                 sample_game_id, sample_ledger_entry_1):
        """Test SessionLedger validation fails when entry has wrong session ID."""
        # Create entry with different session ID
        different_session_entry = LedgerEntry.create_new(
            session_id=str(uuid4()),  # Different session ID!
            player_id=str(uuid4()),
            game_id=sample_game_id,
            external_id="other-session",
            game_number=99,
            display_name="Wrong Session Player",
            session_names=["Wrong"],
            buy_in_sum=1000,
            cash_out_sum=1000,
            in_game=0
        )

        with pytest.raises(ValueError, match="does not belong to session"):
            SessionLedger(
                session_reference=sample_session_reference,
                game_id=sample_game_id,
                entries=[different_session_entry]
            )

    def test_add_entry_success(self, sample_session_ledger, sample_ledger_entry_1):
        """Test add_entry successfully adds new entry."""
        updated_ledger = sample_session_ledger.add_entry(sample_ledger_entry_1)

        # Original ledger should be unchanged (immutability)
        assert len(sample_session_ledger.entries) == 0

        # New ledger should have the entry
        assert len(updated_ledger.entries) == 1
        assert updated_ledger.entries[0] == sample_ledger_entry_1

    def test_add_entry_wrong_session(self, sample_session_ledger, sample_game_id):
        """Test add_entry fails when entry has wrong session ID."""
        wrong_session_entry = LedgerEntry.create_new(
            session_id=str(uuid4()),  # Different session!
            player_id=str(uuid4()),
            game_id=sample_game_id,
            external_id="wrong-session",
            game_number=99,
            display_name="Wrong Player",
            session_names=["Wrong"],
            buy_in_sum=1000,
            cash_out_sum=1000,
            in_game=0
        )

        with pytest.raises(ValueError, match="Entry must belong to this session"):
            sample_session_ledger.add_entry(wrong_session_entry)

    def test_add_entry_duplicate(self, sample_session_ledger, sample_ledger_entry_1):
        """Test add_entry fails when trying to add duplicate entry."""
        # Add entry once
        ledger_with_entry = sample_session_ledger.add_entry(sample_ledger_entry_1)

        # Try to add same entry again
        with pytest.raises(ValueError, match="already exists in session"):
            ledger_with_entry.add_entry(sample_ledger_entry_1)

    def test_remove_entry_success(self, sample_session_ledger, sample_ledger_entry_1):
        """Test remove_entry successfully removes entry."""
        # Add entry first
        ledger_with_entry = sample_session_ledger.add_entry(sample_ledger_entry_1)
        assert len(ledger_with_entry.entries) == 1

        # Remove entry
        updated_ledger = ledger_with_entry.remove_entry(sample_ledger_entry_1.id)

        # Entry should be removed
        assert len(updated_ledger.entries) == 0

    def test_remove_entry_not_found(self, sample_session_ledger):
        """Test remove_entry fails when entry doesn't exist."""
        non_existent_id = LedgerEntryId(
            session_id=str(uuid4()),
            player_id=str(uuid4())
        )

        with pytest.raises(ValueError, match="not found in session"):
            sample_session_ledger.remove_entry(non_existent_id)

    def test_get_entry_success(self, sample_session_ledger, sample_ledger_entry_1):
        """Test get_entry finds entry by player ID."""
        ledger_with_entry = sample_session_ledger.add_entry(sample_ledger_entry_1)

        found_entry = ledger_with_entry.get_entry(sample_ledger_entry_1.get_player_id())
        assert found_entry == sample_ledger_entry_1

    def test_get_entry_not_found(self, sample_session_ledger):
        """Test get_entry returns None when player not found."""
        result = sample_session_ledger.get_entry("non-existent-player")
        assert result is None

    def test_get_player_count_empty(self, sample_session_ledger):
        """Test get_player_count returns 0 for empty session."""
        assert sample_session_ledger.get_player_count() == 0

    def test_get_player_count_with_entries(self, sample_session_ledger,
                                          sample_ledger_entry_1, sample_ledger_entry_2):
        """Test get_player_count returns correct count."""
        ledger = sample_session_ledger.add_entry(sample_ledger_entry_1)
        ledger = ledger.add_entry(sample_ledger_entry_2)

        assert ledger.get_player_count() == 2

    def test_is_empty_true(self, sample_session_ledger):
        """Test is_empty returns True for empty session."""
        assert sample_session_ledger.is_empty() is True

    def test_is_empty_false(self, sample_session_ledger, sample_ledger_entry_1):
        """Test is_empty returns False for session with entries."""
        ledger_with_entry = sample_session_ledger.add_entry(sample_ledger_entry_1)
        assert ledger_with_entry.is_empty() is False

    def test_calculate_total_pot(self, sample_session_ledger,
                               sample_ledger_entry_1, sample_ledger_entry_2):
        """Test calculate_total_pot sums all buy-ins."""
        ledger = sample_session_ledger.add_entry(sample_ledger_entry_1)  # 10000
        ledger = ledger.add_entry(sample_ledger_entry_2)  # 8000

        total_pot = ledger.calculate_total_pot()
        assert total_pot == 18000  # 10000 + 8000

    def test_calculate_total_pot_empty(self, sample_session_ledger):
        """Test calculate_total_pot returns 0 for empty session."""
        assert sample_session_ledger.calculate_total_pot() == 0

    def test_get_profitable_players(self, sample_session_ledger,
                                   sample_ledger_entry_1, sample_ledger_entry_2):
        """Test get_profitable_players returns only profitable entries."""
        # sample_ledger_entry_1: net = +2000 (profitable)
        # sample_ledger_entry_2: net = -1500 (losing)

        ledger = sample_session_ledger.add_entry(sample_ledger_entry_1)
        ledger = ledger.add_entry(sample_ledger_entry_2)

        profitable = ledger.get_profitable_players()
        assert len(profitable) == 1
        assert profitable[0] == sample_ledger_entry_1

    def test_get_losing_players(self, sample_session_ledger,
                               sample_ledger_entry_1, sample_ledger_entry_2):
        """Test get_losing_players returns only losing entries."""
        # sample_ledger_entry_1: net = +2000 (profitable)
        # sample_ledger_entry_2: net = -1500 (losing)

        ledger = sample_session_ledger.add_entry(sample_ledger_entry_1)
        ledger = ledger.add_entry(sample_ledger_entry_2)

        losing = ledger.get_losing_players()
        assert len(losing) == 1
        assert losing[0] == sample_ledger_entry_2

    def test_str_representation(self, sample_session_ledger, sample_ledger_entry_1):
        """Test string representation of SessionLedger."""
        empty_str = str(sample_session_ledger)
        assert "SessionLedger(Session 3, 0 players)" == empty_str

        ledger_with_entry = sample_session_ledger.add_entry(sample_ledger_entry_1)
        with_entry_str = str(ledger_with_entry)
        assert "SessionLedger(Session 3, 1 players)" == with_entry_str