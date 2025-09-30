"""
Comprehensive unit tests for ledger domain services.

Tests business logic, validation rules, and repository interactions
for LedgerManagementService.
"""

import pytest
from unittest.mock import Mock, MagicMock
from uuid import uuid4

from domain.poker.value_objects import GameId
from domain.poker.exceptions import RepositoryError
from domain.ledger.services import LedgerManagementService
from domain.ledger.entities import LedgerEntry, SessionLedger
from domain.ledger.value_objects import (
    LedgerEntryId, SessionReference, PlayerNames, FinancialSummary
)


class TestLedgerManagementService:
    """Test cases for LedgerManagementService."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock ledger repository."""
        return Mock()

    @pytest.fixture
    def service(self, mock_repository):
        """Create a LedgerManagementService instance with mock repository."""
        return LedgerManagementService(mock_repository)

    @pytest.fixture
    def sample_game_id(self):
        return GameId(str(uuid4()))

    @pytest.fixture
    def sample_ledger_entry(self, sample_game_id):
        """Create a sample ledger entry for testing."""
        session_id = str(uuid4())
        player_id = str(uuid4())

        return LedgerEntry.create_new(
            session_id=session_id,
            player_id=player_id,
            game_id=sample_game_id,
            external_id="test-session-123",
            game_number=5,
            display_name="Test Player",
            session_names=["TestPlayer", "TP"],
            buy_in_sum=10000,
            cash_out_sum=12000,
            in_game=0
        )

    @pytest.fixture
    def sample_losing_entry(self, sample_game_id):
        """Create a sample losing ledger entry for testing."""
        session_id = str(uuid4())
        player_id = str(uuid4())

        return LedgerEntry.create_new(
            session_id=session_id,
            player_id=player_id,
            game_id=sample_game_id,
            external_id="test-session-456",
            game_number=6,
            display_name="Losing Player",
            session_names=["LosingPlayer"],
            buy_in_sum=15000,
            cash_out_sum=8000,
            in_game=0
        )

    def test_service_initialization(self, mock_repository):
        """Test service initialization with repository."""
        service = LedgerManagementService(mock_repository)
        assert service.ledger_repository == mock_repository

    def test_get_game_ledger_success(self, service, mock_repository, sample_ledger_entry):
        """Test get_game_ledger returns entries from repository."""
        public_code = "ABCDE"
        expected_entries = [sample_ledger_entry]
        mock_repository.get_all_entries_for_game.return_value = expected_entries

        result = service.get_game_ledger(public_code)

        mock_repository.get_all_entries_for_game.assert_called_once_with(public_code)
        assert result == expected_entries

    def test_get_game_ledger_empty(self, service, mock_repository):
        """Test get_game_ledger returns empty list when no entries."""
        public_code = "EMPTY"
        mock_repository.get_all_entries_for_game.return_value = []

        result = service.get_game_ledger(public_code)

        mock_repository.get_all_entries_for_game.assert_called_once_with(public_code)
        assert result == []

    def test_get_ledger_entry_found(self, service, mock_repository, sample_ledger_entry):
        """Test get_ledger_entry returns entry when found."""
        session_id = sample_ledger_entry.get_session_id()
        player_id = sample_ledger_entry.get_player_id()
        expected_entry_id = LedgerEntryId(session_id=session_id, player_id=player_id)

        mock_repository.get_entry_by_id.return_value = sample_ledger_entry

        result = service.get_ledger_entry(session_id, player_id)

        mock_repository.get_entry_by_id.assert_called_once_with(expected_entry_id)
        assert result == sample_ledger_entry

    def test_get_ledger_entry_not_found(self, service, mock_repository):
        """Test get_ledger_entry returns None when entry not found."""
        session_id = str(uuid4())
        player_id = str(uuid4())
        expected_entry_id = LedgerEntryId(session_id=session_id, player_id=player_id)

        mock_repository.get_entry_by_id.return_value = None

        result = service.get_ledger_entry(session_id, player_id)

        mock_repository.get_entry_by_id.assert_called_once_with(expected_entry_id)
        assert result is None

    def test_update_ledger_entry_success(self, service, mock_repository, sample_ledger_entry):
        """Test successful ledger entry update."""
        session_id = sample_ledger_entry.get_session_id()
        player_id = sample_ledger_entry.get_player_id()
        updates = {"buy_in_sum": 15000, "cash_out_sum": 18000}

        # Mock repository responses
        mock_repository.get_entry_by_id.return_value = sample_ledger_entry
        mock_repository.save_entry.return_value = sample_ledger_entry  # In real scenario, this would be updated

        result = service.update_ledger_entry(session_id, player_id, updates)

        # Verify repository calls
        mock_repository.get_entry_by_id.assert_called_once()
        mock_repository.save_entry.assert_called_once()

        # Verify the save_entry was called with an updated entry
        saved_entry = mock_repository.save_entry.call_args[0][0]
        assert saved_entry.financial_summary.buy_in_sum == 15000
        assert saved_entry.financial_summary.cash_out_sum == 18000

    def test_update_ledger_entry_not_found(self, service, mock_repository):
        """Test update_ledger_entry raises ValueError when entry not found."""
        session_id = str(uuid4())
        player_id = str(uuid4())
        updates = {"buy_in_sum": 5000}

        mock_repository.get_entry_by_id.return_value = None

        with pytest.raises(ValueError, match="Ledger entry not found"):
            service.update_ledger_entry(session_id, player_id, updates)

        # Should not try to save if entry not found
        mock_repository.save_entry.assert_not_called()

    def test_update_ledger_entry_financial_updates(self, service, mock_repository, sample_ledger_entry):
        """Test update_ledger_entry with various financial field updates."""
        session_id = sample_ledger_entry.get_session_id()
        player_id = sample_ledger_entry.get_player_id()

        mock_repository.get_entry_by_id.return_value = sample_ledger_entry
        mock_repository.save_entry.return_value = sample_ledger_entry

        # Test individual field updates
        updates = {"buy_in_sum": 8000}
        service.update_ledger_entry(session_id, player_id, updates)

        saved_entry = mock_repository.save_entry.call_args[0][0]
        assert saved_entry.financial_summary.buy_in_sum == 8000

        # Test multiple field updates
        updates = {"cash_out_sum": 9000, "in_game": 1000}
        service.update_ledger_entry(session_id, player_id, updates)

        saved_entry = mock_repository.save_entry.call_args[0][0]
        assert saved_entry.financial_summary.cash_out_sum == 9000
        assert saved_entry.financial_summary.in_game == 1000

    def test_update_ledger_entry_names_update(self, service, mock_repository, sample_ledger_entry):
        """Test update_ledger_entry with names update."""
        session_id = sample_ledger_entry.get_session_id()
        player_id = sample_ledger_entry.get_player_id()
        new_names = ["NewName1", "NewName2", "NN"]

        mock_repository.get_entry_by_id.return_value = sample_ledger_entry
        mock_repository.save_entry.return_value = sample_ledger_entry

        updates = {"names": new_names}
        service.update_ledger_entry(session_id, player_id, updates)

        saved_entry = mock_repository.save_entry.call_args[0][0]
        assert saved_entry.player_names.session_names == new_names

    def test_update_ledger_entry_invalid_names_type(self, service, mock_repository, sample_ledger_entry):
        """Test update_ledger_entry raises ValueError for invalid names type."""
        session_id = sample_ledger_entry.get_session_id()
        player_id = sample_ledger_entry.get_player_id()

        mock_repository.get_entry_by_id.return_value = sample_ledger_entry

        updates = {"names": "not-a-list"}

        with pytest.raises(ValueError, match="Names must be a list"):
            service.update_ledger_entry(session_id, player_id, updates)

    def test_update_ledger_entry_validation_failure(self, service, mock_repository, sample_ledger_entry):
        """Test update_ledger_entry validation prevents negative buy-in."""
        session_id = sample_ledger_entry.get_session_id()
        player_id = sample_ledger_entry.get_player_id()

        mock_repository.get_entry_by_id.return_value = sample_ledger_entry

        # Try to set negative buy-in
        updates = {"buy_in_sum": -5000}

        with pytest.raises(ValueError, match="Buy-in amount cannot be negative"):
            service.update_ledger_entry(session_id, player_id, updates)

        mock_repository.save_entry.assert_not_called()

    def test_update_ledger_entry_repository_error(self, service, mock_repository, sample_ledger_entry):
        """Test update_ledger_entry propagates repository errors."""
        session_id = sample_ledger_entry.get_session_id()
        player_id = sample_ledger_entry.get_player_id()
        updates = {"buy_in_sum": 5000}

        mock_repository.get_entry_by_id.return_value = sample_ledger_entry
        mock_repository.save_entry.side_effect = RepositoryError("Save failed")

        with pytest.raises(RepositoryError, match="Save failed"):
            service.update_ledger_entry(session_id, player_id, updates)

    def test_delete_ledger_entry_success(self, service, mock_repository):
        """Test successful deletion of ledger entry."""
        session_id = str(uuid4())
        player_id = str(uuid4())
        expected_entry_id = LedgerEntryId(session_id=session_id, player_id=player_id)

        mock_repository.delete_entry.return_value = True

        result = service.delete_ledger_entry(session_id, player_id)

        mock_repository.delete_entry.assert_called_once_with(expected_entry_id)
        assert result is True

    def test_delete_ledger_entry_not_found(self, service, mock_repository):
        """Test deletion returns False when entry doesn't exist."""
        session_id = str(uuid4())
        player_id = str(uuid4())
        expected_entry_id = LedgerEntryId(session_id=session_id, player_id=player_id)

        mock_repository.delete_entry.return_value = False

        result = service.delete_ledger_entry(session_id, player_id)

        mock_repository.delete_entry.assert_called_once_with(expected_entry_id)
        assert result is False

    def test_delete_ledger_entry_repository_error(self, service, mock_repository):
        """Test delete_ledger_entry propagates repository errors."""
        session_id = str(uuid4())
        player_id = str(uuid4())

        mock_repository.delete_entry.side_effect = RepositoryError("Delete failed")

        with pytest.raises(RepositoryError, match="Delete failed"):
            service.delete_ledger_entry(session_id, player_id)

    def test_delete_entire_session_success(self, service, mock_repository):
        """Test successful deletion of entire session."""
        session_id = str(uuid4())
        expected_delete_count = 3

        mock_repository.delete_session_entries.return_value = expected_delete_count

        result = service.delete_entire_session(session_id)

        mock_repository.delete_session_entries.assert_called_once_with(session_id)
        assert result == expected_delete_count

    def test_delete_entire_session_no_entries(self, service, mock_repository):
        """Test deletion of session with no entries."""
        session_id = str(uuid4())

        mock_repository.delete_session_entries.return_value = 0

        result = service.delete_entire_session(session_id)

        mock_repository.delete_session_entries.assert_called_once_with(session_id)
        assert result == 0

    def test_delete_entire_session_repository_error(self, service, mock_repository):
        """Test delete_entire_session propagates repository errors."""
        session_id = str(uuid4())

        mock_repository.delete_session_entries.side_effect = RepositoryError("Session delete failed")

        with pytest.raises(RepositoryError, match="Session delete failed"):
            service.delete_entire_session(session_id)

    def test_get_session_ledger_found(self, service, mock_repository):
        """Test get_session_ledger returns SessionLedger when found."""
        session_id = str(uuid4())
        expected_session_ledger = Mock(spec=SessionLedger)

        mock_repository.get_session_ledger.return_value = expected_session_ledger

        result = service.get_session_ledger(session_id)

        mock_repository.get_session_ledger.assert_called_once_with(session_id)
        assert result == expected_session_ledger

    def test_get_session_ledger_not_found(self, service, mock_repository):
        """Test get_session_ledger returns None when session not found."""
        session_id = str(uuid4())

        mock_repository.get_session_ledger.return_value = None

        result = service.get_session_ledger(session_id)

        mock_repository.get_session_ledger.assert_called_once_with(session_id)
        assert result is None

    def test_check_session_orphaned_true(self, service, mock_repository):
        """Test check_session_orphaned returns True when session has no players."""
        session_id = str(uuid4())

        mock_repository.session_has_players.return_value = False

        result = service.check_session_orphaned(session_id)

        mock_repository.session_has_players.assert_called_once_with(session_id)
        assert result is True

    def test_check_session_orphaned_false(self, service, mock_repository):
        """Test check_session_orphaned returns False when session has players."""
        session_id = str(uuid4())

        mock_repository.session_has_players.return_value = True

        result = service.check_session_orphaned(session_id)

        mock_repository.session_has_players.assert_called_once_with(session_id)
        assert result is False

    def test_get_player_entries_in_game_success(self, service, mock_repository, sample_ledger_entry):
        """Test get_player_entries_in_game returns player's entries."""
        public_code = "ABCDE"
        player_id = sample_ledger_entry.get_player_id()
        expected_entries = [sample_ledger_entry]

        mock_repository.get_entries_for_player_in_game.return_value = expected_entries

        result = service.get_player_entries_in_game(public_code, player_id)

        mock_repository.get_entries_for_player_in_game.assert_called_once_with(public_code, player_id)
        assert result == expected_entries

    def test_get_player_entries_in_game_empty(self, service, mock_repository):
        """Test get_player_entries_in_game returns empty list when no entries."""
        public_code = "EMPTY"
        player_id = str(uuid4())

        mock_repository.get_entries_for_player_in_game.return_value = []

        result = service.get_player_entries_in_game(public_code, player_id)

        mock_repository.get_entries_for_player_in_game.assert_called_once_with(public_code, player_id)
        assert result == []

    def test_calculate_game_statistics_empty_game(self, service, mock_repository):
        """Test calculate_game_statistics returns zero stats for empty game."""
        public_code = "EMPTY"

        mock_repository.get_all_entries_for_game.return_value = []

        result = service.calculate_game_statistics(public_code)

        expected = {
            "total_entries": 0,
            "total_sessions": 0,
            "total_players": 0,
            "total_pot_cents": 0,
            "profitable_entries": 0,
            "losing_entries": 0
        }

        assert result == expected

    def test_calculate_game_statistics_with_data(self, service, mock_repository,
                                               sample_ledger_entry, sample_losing_entry):
        """Test calculate_game_statistics with actual data."""
        public_code = "ABCDE"

        # Create additional entries to test statistics
        # sample_ledger_entry: profitable (+2000)
        # sample_losing_entry: losing (-7000)
        # Create break-even entry
        break_even_entry = LedgerEntry.create_new(
            session_id=str(uuid4()),
            player_id=str(uuid4()),
            game_id=GameId(str(uuid4())),
            external_id="break-even-session",
            game_number=7,
            display_name="Break Even Player",
            session_names=["BreakEven"],
            buy_in_sum=5000,
            cash_out_sum=3000,
            in_game=2000  # Net = 0
        )

        all_entries = [sample_ledger_entry, sample_losing_entry, break_even_entry]
        mock_repository.get_all_entries_for_game.return_value = all_entries

        result = service.calculate_game_statistics(public_code)

        expected = {
            "total_entries": 3,
            "total_sessions": 3,  # All have different session IDs
            "total_players": 3,  # All have different player IDs
            "total_pot_cents": 30000,  # 10000 + 15000 + 5000
            "total_pot_dollars": 300.0,
            "profitable_entries": 1,  # sample_ledger_entry
            "losing_entries": 1,  # sample_losing_entry
            "break_even_entries": 1  # break_even_entry
        }

        assert result == expected

    def test_calculate_game_statistics_overlapping_players_sessions(self, service, mock_repository, sample_game_id):
        """Test statistics calculation with overlapping players and sessions."""
        public_code = "OVERLAP"

        # Same player in different sessions
        player_id = str(uuid4())
        session_1_id = str(uuid4())
        session_2_id = str(uuid4())

        entry_1 = LedgerEntry.create_new(
            session_id=session_1_id,
            player_id=player_id,
            game_id=sample_game_id,
            external_id="session-1",
            game_number=1,
            display_name="Repeat Player",
            session_names=["Player"],
            buy_in_sum=5000,
            cash_out_sum=6000,
            in_game=0
        )

        entry_2 = LedgerEntry.create_new(
            session_id=session_2_id,
            player_id=player_id,
            game_id=sample_game_id,
            external_id="session-2",
            game_number=2,
            display_name="Repeat Player",
            session_names=["Player"],
            buy_in_sum=8000,
            cash_out_sum=7000,
            in_game=0
        )

        all_entries = [entry_1, entry_2]
        mock_repository.get_all_entries_for_game.return_value = all_entries

        result = service.calculate_game_statistics(public_code)

        # Should have 2 entries, 2 sessions, but only 1 unique player
        assert result["total_entries"] == 2
        assert result["total_sessions"] == 2
        assert result["total_players"] == 1  # Same player in both sessions

    def test_apply_updates_financial_only(self, service, sample_ledger_entry):
        """Test _apply_updates with only financial updates."""
        updates = {
            "buy_in_sum": 8000,
            "cash_out_sum": 10000,
            "in_game": 500
        }

        result = service._apply_updates(sample_ledger_entry, updates)

        assert result.financial_summary.buy_in_sum == 8000
        assert result.financial_summary.cash_out_sum == 10000
        assert result.financial_summary.in_game == 500
        assert result.financial_summary.net == 2500  # 10000 + 500 - 8000

    def test_apply_updates_names_only(self, service, sample_ledger_entry):
        """Test _apply_updates with only names update."""
        new_names = ["UpdatedName1", "UpdatedName2"]
        updates = {"names": new_names}

        result = service._apply_updates(sample_ledger_entry, updates)

        assert result.player_names.session_names == new_names
        # Financial data should be unchanged
        assert result.financial_summary.buy_in_sum == sample_ledger_entry.financial_summary.buy_in_sum

    def test_apply_updates_mixed(self, service, sample_ledger_entry):
        """Test _apply_updates with both financial and names updates."""
        updates = {
            "buy_in_sum": 12000,
            "names": ["MixedUpdate"]
        }

        result = service._apply_updates(sample_ledger_entry, updates)

        assert result.financial_summary.buy_in_sum == 12000
        assert result.player_names.session_names == ["MixedUpdate"]

    def test_apply_updates_no_changes(self, service, sample_ledger_entry):
        """Test _apply_updates with no applicable updates."""
        updates = {"irrelevant_field": "value"}

        result = service._apply_updates(sample_ledger_entry, updates)

        # Should return the same entry
        assert result == sample_ledger_entry

    def test_apply_updates_invalid_names_type(self, service, sample_ledger_entry):
        """Test _apply_updates raises ValueError for invalid names type."""
        updates = {"names": "not-a-list"}

        with pytest.raises(ValueError, match="Names must be a list"):
            service._apply_updates(sample_ledger_entry, updates)

    def test_validate_ledger_entry_success(self, service, sample_ledger_entry):
        """Test _validate_ledger_entry passes for valid entry."""
        # Should not raise any exceptions
        service._validate_ledger_entry(sample_ledger_entry)

    def test_validate_ledger_entry_negative_buy_in(self, service, sample_game_id):
        """Test _validate_ledger_entry fails for negative buy-in."""
        # Create entry with negative buy-in
        invalid_entry = LedgerEntry.create_new(
            session_id=str(uuid4()),
            player_id=str(uuid4()),
            game_id=sample_game_id,
            external_id="invalid-session",
            game_number=1,
            display_name="Invalid Player",
            session_names=["Invalid"],
            buy_in_sum=-5000,  # Negative!
            cash_out_sum=0,
            in_game=0
        )

        with pytest.raises(ValueError, match="Buy-in amount cannot be negative"):
            service._validate_ledger_entry(invalid_entry)

    def test_validate_ledger_entry_empty_names(self, service, sample_game_id):
        """Test _validate_ledger_entry fails for empty session names."""
        # This test verifies the validation, but FinancialSummary.create
        # and PlayerNames validation will prevent this case normally

        # We need to manually construct an invalid entry
        entry_id = LedgerEntryId(session_id=str(uuid4()), player_id=str(uuid4()))
        session_ref = SessionReference(
            session_id=entry_id.session_id,
            external_id="test-session",
            game_number=1
        )

        # Create PlayerNames with valid construction but then manually modify
        player_names = PlayerNames(
            display_name="Test Player",
            session_names=["Initial"]
        )

        # Manually create empty names by bypassing validation
        # Since PlayerNames is frozen, we create a mock instead
        empty_names = Mock(spec=PlayerNames)
        empty_names.display_name = "Test Player"
        empty_names.session_names = []

        financial_summary = FinancialSummary.create(
            buy_in_sum=5000,
            cash_out_sum=5000,
            in_game=0
        )

        # Create entry manually with invalid names
        invalid_entry = Mock(spec=LedgerEntry)
        invalid_entry.financial_summary = financial_summary
        invalid_entry.player_names = empty_names

        with pytest.raises(ValueError, match="Player must have at least one session name"):
            service._validate_ledger_entry(invalid_entry)