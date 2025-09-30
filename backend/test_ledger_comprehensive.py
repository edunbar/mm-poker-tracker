"""Comprehensive tests for ledger_service_v2 to achieve 90%+ coverage."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
import uuid

# Import for coverage
import src.services.ledger_service_v2
from src.services.ledger_service_v2 import (
    LedgerService,
    get_all_session_summaries,
    update_session_summary,
    delete_session_summary,
    delete_entire_session,
    get_session_summary
)
from src.domain.poker.exceptions import RepositoryError


class TestLedgerServiceComprehensive:
    """Comprehensive tests for LedgerService to achieve 90%+ coverage."""

    @pytest.fixture
    def service(self):
        """Create service with mocked dependencies."""
        mock_session = Mock()
        with patch('src.services.ledger_service_v2.SQLAlchemyLedgerRepository') as mock_repo_class, \
             patch('src.services.ledger_service_v2.LedgerManagementService') as mock_domain_class:

            mock_repo = Mock()
            mock_domain = Mock()
            mock_repo_class.return_value = mock_repo
            mock_domain_class.return_value = mock_domain

            service = LedgerService(mock_session)
            service._repository = mock_repo
            service._domain_service = mock_domain
            return service

    @pytest.fixture
    def mock_ledger_entry(self):
        """Create a mock ledger entry."""
        entry = Mock()
        entry.to_dict.return_value = {
            "session_id": "session-123",
            "player_id": "player-456",
            "buy_in_sum": 5000,
            "cash_out_sum": 6000,
            "display_name": "Test Player"
        }
        return entry

    def test_init_with_provided_session(self):
        """Test initialization with provided session."""
        mock_session = Mock()
        with patch('src.services.ledger_service_v2.SQLAlchemyLedgerRepository'), \
             patch('src.services.ledger_service_v2.LedgerManagementService'):

            service = LedgerService(mock_session)
            assert service._db_session == mock_session
            assert service._should_close_session is False

    def test_init_without_session(self):
        """Test initialization without session creates new one."""
        mock_session = Mock()
        with patch('src.services.ledger_service_v2.SessionLocal', return_value=mock_session), \
             patch('src.services.ledger_service_v2.SQLAlchemyLedgerRepository'), \
             patch('src.services.ledger_service_v2.LedgerManagementService'):

            service = LedgerService()
            assert service._db_session == mock_session
            assert service._should_close_session is True

    def test_context_manager_with_provided_session(self):
        """Test context manager doesn't close provided session."""
        mock_session = Mock()
        with patch('src.services.ledger_service_v2.SQLAlchemyLedgerRepository'), \
             patch('src.services.ledger_service_v2.LedgerManagementService'):

            with LedgerService(mock_session) as service:
                assert service._db_session == mock_session

            # Should not close provided session
            mock_session.close.assert_not_called()

    def test_context_manager_with_created_session(self):
        """Test context manager closes created session."""
        mock_session = Mock()
        with patch('src.services.ledger_service_v2.SessionLocal', return_value=mock_session), \
             patch('src.services.ledger_service_v2.SQLAlchemyLedgerRepository'), \
             patch('src.services.ledger_service_v2.LedgerManagementService'):

            with LedgerService() as service:
                assert service._db_session == mock_session

            # Should close created session
            mock_session.close.assert_called_once()

    def test_get_all_session_summaries_success(self, service, mock_ledger_entry):
        """Test successful get_all_session_summaries."""
        service._domain_service.get_game_ledger.return_value = [mock_ledger_entry]

        result = service.get_all_session_summaries("ABC123")

        service._domain_service.get_game_ledger.assert_called_once_with("ABC123")
        assert result["total_count"] == 1
        assert len(result["summaries"]) == 1
        assert result["summaries"][0]["session_id"] == "session-123"

    def test_get_all_session_summaries_empty(self, service):
        """Test get_all_session_summaries with no results."""
        service._domain_service.get_game_ledger.return_value = []

        result = service.get_all_session_summaries("ABC123")

        assert result["summaries"] == []
        assert result["total_count"] == 0

    def test_get_all_session_summaries_repository_error(self, service):
        """Test get_all_session_summaries with repository error."""
        service._domain_service.get_game_ledger.side_effect = RepositoryError("Database error")

        with pytest.raises(Exception, match="Error fetching session summaries"):
            service.get_all_session_summaries("ABC123")

    def test_get_all_session_summaries_generic_error(self, service):
        """Test get_all_session_summaries with generic error."""
        service._domain_service.get_game_ledger.side_effect = ValueError("Generic error")

        with pytest.raises(ValueError):
            service.get_all_session_summaries("ABC123")

    def test_update_session_summary_success(self, service):
        """Test successful update_session_summary."""
        mock_entry = Mock()
        mock_entry.to_dict.return_value = {"session_id": "session-123", "updated": True}
        service._domain_service.update_ledger_entry.return_value = mock_entry

        updates = {"display_name": "New Name", "buy_in_sum": 6000}
        result = service.update_session_summary("session-123", "player-456", updates)

        service._domain_service.update_ledger_entry.assert_called_once_with(
            "session-123", "player-456", updates
        )
        assert result["session_id"] == "session-123"
        assert result["updated"] is True

    def test_update_session_summary_not_found(self, service):
        """Test update_session_summary when entry not found."""
        service._domain_service.update_ledger_entry.return_value = None

        updates = {"display_name": "New Name"}
        result = service.update_session_summary("session-123", "player-456", updates)

        assert result is None

    def test_update_session_summary_repository_error(self, service):
        """Test update_session_summary with repository error."""
        service._domain_service.update_ledger_entry.side_effect = RepositoryError("Database error")

        updates = {"display_name": "New Name"}
        with pytest.raises(Exception, match="Error updating session summary"):
            service.update_session_summary("session-123", "player-456", updates)

    def test_update_session_summary_generic_error(self, service):
        """Test update_session_summary with generic error."""
        service._domain_service.update_ledger_entry.side_effect = ValueError("Generic error")

        updates = {"display_name": "New Name"}
        with pytest.raises(ValueError):
            service.update_session_summary("session-123", "player-456", updates)

    def test_delete_session_summary_success(self, service):
        """Test successful delete_session_summary."""
        service._domain_service.delete_ledger_entry.return_value = True

        result = service.delete_session_summary("session-123", "player-456")

        service._domain_service.delete_ledger_entry.assert_called_once_with("session-123", "player-456")
        assert result is True

    def test_delete_session_summary_not_found(self, service):
        """Test delete_session_summary when entry not found."""
        service._domain_service.delete_ledger_entry.return_value = False

        result = service.delete_session_summary("session-123", "player-456")

        assert result is False

    def test_delete_session_summary_repository_error(self, service):
        """Test delete_session_summary with repository error."""
        service._domain_service.delete_ledger_entry.side_effect = RepositoryError("Database error")

        with pytest.raises(Exception, match="Error deleting session summary"):
            service.delete_session_summary("session-123", "player-456")

    def test_delete_session_summary_generic_error(self, service):
        """Test delete_session_summary with generic error."""
        service._domain_service.delete_ledger_entry.side_effect = ValueError("Generic error")

        with pytest.raises(ValueError):
            service.delete_session_summary("session-123", "player-456")

    def test_delete_entire_session_success(self, service):
        """Test successful delete_entire_session."""
        service._domain_service.delete_session_ledger.return_value = 5

        result = service.delete_entire_session("session-123")

        service._domain_service.delete_session_ledger.assert_called_once_with("session-123")
        assert result == {"deleted_count": 5}

    def test_delete_entire_session_no_entries(self, service):
        """Test delete_entire_session with no entries."""
        service._domain_service.delete_session_ledger.return_value = 0

        result = service.delete_entire_session("session-123")

        assert result == {"deleted_count": 0}

    def test_delete_entire_session_repository_error(self, service):
        """Test delete_entire_session with repository error."""
        service._domain_service.delete_session_ledger.side_effect = RepositoryError("Database error")

        with pytest.raises(Exception, match="Error deleting entire session"):
            service.delete_entire_session("session-123")

    def test_delete_entire_session_generic_error(self, service):
        """Test delete_entire_session with generic error."""
        service._domain_service.delete_session_ledger.side_effect = ValueError("Generic error")

        with pytest.raises(ValueError):
            service.delete_entire_session("session-123")

    def test_get_session_summary_success(self, service, mock_ledger_entry):
        """Test successful get_session_summary."""
        service._domain_service.get_session_ledger.return_value = [mock_ledger_entry]

        result = service.get_session_summary("session-123")

        service._domain_service.get_session_ledger.assert_called_once_with("session-123")
        assert len(result) == 1
        assert result[0]["session_id"] == "session-123"

    def test_get_session_summary_empty(self, service):
        """Test get_session_summary with no results."""
        service._domain_service.get_session_ledger.return_value = []

        result = service.get_session_summary("session-123")

        assert result == []

    def test_get_session_summary_repository_error(self, service):
        """Test get_session_summary with repository error."""
        service._domain_service.get_session_ledger.side_effect = RepositoryError("Database error")

        with pytest.raises(Exception, match="Error fetching session summary"):
            service.get_session_summary("session-123")

    def test_get_session_summary_generic_error(self, service):
        """Test get_session_summary with generic error."""
        service._domain_service.get_session_ledger.side_effect = ValueError("Generic error")

        with pytest.raises(ValueError):
            service.get_session_summary("session-123")

    def test_get_game_statistics_success(self, service):
        """Test successful get_game_statistics."""
        mock_stats = {
            "total_sessions": 10,
            "total_players": 25,
            "total_buy_ins": 50000,
            "total_cash_outs": 48000
        }
        service._domain_service.get_game_statistics.return_value = mock_stats

        result = service.get_game_statistics("ABC123")

        service._domain_service.get_game_statistics.assert_called_once_with("ABC123")
        assert result == mock_stats

    def test_get_game_statistics_repository_error(self, service):
        """Test get_game_statistics with repository error."""
        service._domain_service.get_game_statistics.side_effect = RepositoryError("Database error")

        with pytest.raises(Exception, match="Error fetching game statistics"):
            service.get_game_statistics("ABC123")

    def test_get_game_statistics_generic_error(self, service):
        """Test get_game_statistics with generic error."""
        service._domain_service.get_game_statistics.side_effect = ValueError("Generic error")

        with pytest.raises(ValueError):
            service.get_game_statistics("ABC123")


class TestLedgerServiceLegacyFunctions:
    """Test legacy compatibility functions."""

    def test_get_all_session_summaries_function(self):
        """Test legacy get_all_session_summaries function."""
        with patch.object(LedgerService, '__enter__') as mock_enter, \
             patch.object(LedgerService, '__exit__') as mock_exit:

            mock_service = Mock()
            mock_enter.return_value = mock_service
            mock_service.get_all_session_summaries.return_value = {"summaries": [], "total_count": 0}

            result = get_all_session_summaries("ABC123")

            assert result == {"summaries": [], "total_count": 0}
            mock_service.get_all_session_summaries.assert_called_once_with("ABC123")

    def test_update_session_summary_function(self):
        """Test legacy update_session_summary function."""
        with patch.object(LedgerService, '__enter__') as mock_enter, \
             patch.object(LedgerService, '__exit__') as mock_exit:

            mock_service = Mock()
            mock_enter.return_value = mock_service
            mock_service.update_session_summary.return_value = {"updated": True}

            updates = {"display_name": "New Name"}
            result = update_session_summary("session-123", "player-456", updates)

            assert result == {"updated": True}
            mock_service.update_session_summary.assert_called_once_with("session-123", "player-456", updates)

    def test_delete_session_summary_function(self):
        """Test legacy delete_session_summary function."""
        with patch.object(LedgerService, '__enter__') as mock_enter, \
             patch.object(LedgerService, '__exit__') as mock_exit:

            mock_service = Mock()
            mock_enter.return_value = mock_service
            mock_service.delete_session_summary.return_value = True

            result = delete_session_summary("session-123", "player-456")

            assert result is True
            mock_service.delete_session_summary.assert_called_once_with("session-123", "player-456")

    def test_delete_entire_session_function(self):
        """Test legacy delete_entire_session function."""
        with patch.object(LedgerService, '__enter__') as mock_enter, \
             patch.object(LedgerService, '__exit__') as mock_exit:

            mock_service = Mock()
            mock_enter.return_value = mock_service
            mock_service.delete_entire_session.return_value = {"deleted_count": 5}

            result = delete_entire_session("session-123")

            assert result == {"deleted_count": 5}
            mock_service.delete_entire_session.assert_called_once_with("session-123")

    def test_get_session_summary_function(self):
        """Test legacy get_session_summary function."""
        with patch.object(LedgerService, '__enter__') as mock_enter, \
             patch.object(LedgerService, '__exit__') as mock_exit:

            mock_service = Mock()
            mock_enter.return_value = mock_service
            mock_service.get_session_summary.return_value = [{"session_id": "session-123"}]

            result = get_session_summary("session-123")

            assert result == [{"session_id": "session-123"}]
            mock_service.get_session_summary.assert_called_once_with("session-123")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])