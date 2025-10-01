"""Advanced tests for ledger_service_v2 to reach 80% coverage."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pytest
from unittest.mock import Mock, patch, MagicMock

# Import for coverage
import src.services.ledger_service_v2
from src.services.ledger_service_v2 import LedgerService
from src.domain.poker.exceptions import RepositoryError


class TestLedgerServiceAdvanced:
    """Advanced tests targeting missing coverage lines."""

    @pytest.fixture
    def service(self):
        """Create service with fully mocked dependencies."""
        mock_session = Mock()

        with patch('src.services.ledger_service_v2.audit_context') as mock_audit, \
             patch('src.services.ledger_service_v2.SQLAlchemyLedgerRepository') as mock_repo_class, \
             patch('src.services.ledger_service_v2.LedgerManagementService') as mock_domain_class:

            # Setup the audit context to just pass through
            mock_audit.return_value.__enter__ = Mock(return_value=None)
            mock_audit.return_value.__exit__ = Mock(return_value=None)

            mock_repo = Mock()
            mock_domain = Mock()
            mock_repo_class.return_value = mock_repo
            mock_domain_class.return_value = mock_domain

            service = LedgerService(mock_session)
            service._repository = mock_repo
            service._domain_service = mock_domain
            return service

    def test_get_all_session_summaries_repository_error(self, service):
        """Test get_all_session_summaries with repository error (lines 82-83)."""
        service._domain_service.get_game_ledger.side_effect = RepositoryError("Database error")

        with pytest.raises(Exception, match="Error fetching session summaries"):
            service.get_all_session_summaries("ABC123")

    def test_update_session_summary_repository_error(self, service):
        """Test update_session_summary with repository error (lines 145-150)."""
        # Mock existing entry for initial validation
        mock_existing_entry = Mock()
        service._domain_service.get_ledger_entry.return_value = mock_existing_entry
        service._get_legacy_field_value = Mock(return_value="old_value")

        # Make the update operation fail
        service._domain_service.update_ledger_entry.side_effect = RepositoryError("Database error")

        updates = {"buy_in_sum": 5000}
        with pytest.raises(Exception, match="Error updating session summary"):
            service.update_session_summary("session-123", "player-456", updates)

    def test_update_session_summary_value_error_propagation(self, service):
        """Test update_session_summary propagates ValueError (lines 145-150)."""
        # Mock existing entry for initial validation
        mock_existing_entry = Mock()
        service._domain_service.get_ledger_entry.return_value = mock_existing_entry
        service._get_legacy_field_value = Mock(return_value="old_value")

        # Make the update operation fail with ValueError
        service._domain_service.update_ledger_entry.side_effect = ValueError("Validation error")

        updates = {"buy_in_sum": 5000}
        with pytest.raises(ValueError, match="Validation error"):
            service.update_session_summary("session-123", "player-456", updates)

    def test_update_session_summary_generic_error_propagation(self, service):
        """Test update_session_summary propagates generic errors (lines 145-150)."""
        # Mock existing entry for initial validation
        mock_existing_entry = Mock()
        service._domain_service.get_ledger_entry.return_value = mock_existing_entry
        service._get_legacy_field_value = Mock(return_value="old_value")

        # Make the update operation fail with generic error
        service._domain_service.update_ledger_entry.side_effect = RuntimeError("System error")

        updates = {"buy_in_sum": 5000}
        with pytest.raises(RuntimeError, match="System error"):
            service.update_session_summary("session-123", "player-456", updates)

    def test_delete_session_summary_repository_error(self, service):
        """Test delete_session_summary with repository error (lines 211-216)."""
        # Mock existing entry for initial validation
        mock_entry = Mock()
        mock_entry.get_session_id.return_value = "session-123"
        mock_entry.get_player_id.return_value = "player-456"
        mock_entry.financial_summary.buy_in_sum = 5000
        mock_entry.financial_summary.cash_out_sum = 6000
        mock_entry.financial_summary.in_game = 0
        mock_entry.financial_summary.net = 1000
        mock_entry.player_names.session_names = ["Test Player"]
        mock_entry.game_id = "game-789"

        service._domain_service.get_ledger_entry.return_value = mock_entry
        service._domain_service.delete_ledger_entry.side_effect = RepositoryError("Database error")

        with pytest.raises(Exception, match="Error deleting session summary"):
            service.delete_session_summary("session-123", "player-456")

    def test_delete_session_summary_value_error_propagation(self, service):
        """Test delete_session_summary propagates ValueError (lines 211-216)."""
        # Mock existing entry for initial validation
        mock_entry = Mock()
        service._domain_service.get_ledger_entry.return_value = mock_entry
        service._domain_service.delete_ledger_entry.side_effect = ValueError("Validation error")

        with pytest.raises(ValueError, match="Validation error"):
            service.delete_session_summary("session-123", "player-456")

    def test_delete_session_summary_generic_error_propagation(self, service):
        """Test delete_session_summary propagates generic errors (lines 211-216)."""
        # Mock existing entry for initial validation
        mock_entry = Mock()
        service._domain_service.get_ledger_entry.return_value = mock_entry
        service._domain_service.delete_ledger_entry.side_effect = RuntimeError("System error")

        with pytest.raises(RuntimeError, match="System error"):
            service.delete_session_summary("session-123", "player-456")

    def test_delete_entire_session_with_entries_processing(self, service):
        """Test delete_entire_session with entry processing (lines 229-290)."""
        # Mock session ledger with entries
        mock_session_ledger = Mock()
        mock_entry1 = Mock()
        mock_entry1.game_id = "game-789"
        mock_entry1.get_player_id.return_value = "player-456"
        mock_entry2 = Mock()
        mock_entry2.game_id = "game-789"
        mock_entry2.get_player_id.return_value = "player-789"

        mock_session_ledger.entries = [mock_entry1, mock_entry2]
        mock_session_ledger.session_reference.session_id = "session-123"
        mock_session_ledger.session_reference.game_id = "game-789"

        service._domain_service.get_session_ledger.return_value = mock_session_ledger
        service._domain_service.delete_session_ledger.return_value = 2

        # Mock private methods
        service._delete_session_model = Mock()
        service._update_payment_balances_after_deletion = Mock()
        service._invalidate_game_cache = Mock()

        result = service.delete_entire_session("session-123")

        assert result["deleted_count"] == 2
        assert result["message"] == "Session deleted successfully"

        # Verify cleanup methods were called for each player
        assert service._update_payment_balances_after_deletion.call_count == 2
        service._delete_session_model.assert_called_once_with("session-123", "game-789")
        service._invalidate_game_cache.assert_called_once_with("game-789")

    def test_delete_entire_session_repository_error(self, service):
        """Test delete_entire_session with repository error (lines 283-284, 286-287)."""
        service._domain_service.get_session_ledger.side_effect = RepositoryError("Database error")

        with pytest.raises(Exception, match="Error deleting entire session"):
            service.delete_entire_session("session-123")

    def test_delete_entire_session_generic_error(self, service):
        """Test delete_entire_session with generic error (lines 286-287)."""
        service._domain_service.get_session_ledger.side_effect = RuntimeError("System error")

        with pytest.raises(RuntimeError, match="System error"):
            service.delete_entire_session("session-123")

    def test_get_session_summary_with_results(self, service):
        """Test get_session_summary with results (lines 304-319)."""
        mock_entry = Mock()
        mock_entry.to_dict.return_value = {"session_id": "session-123", "player_id": "player-456"}
        service._domain_service.get_ledger_entry.return_value = mock_entry

        result = service.get_session_summary("session-123", "player-456")

        assert result == {"session_id": "session-123", "player_id": "player-456"}

    def test_get_session_summary_not_found(self, service):
        """Test get_session_summary when not found (lines 304-319)."""
        service._domain_service.get_ledger_entry.return_value = None

        result = service.get_session_summary("session-123", "player-456")

        assert result is None

    def test_get_session_summary_repository_error(self, service):
        """Test get_session_summary with repository error (lines 334-338)."""
        service._domain_service.get_ledger_entry.side_effect = RepositoryError("Database error")

        with pytest.raises(Exception, match="Error fetching session summary"):
            service.get_session_summary("session-123", "player-456")

    def test_get_session_summary_generic_error(self, service):
        """Test get_session_summary with generic error (lines 334-338)."""
        service._domain_service.get_ledger_entry.side_effect = RuntimeError("System error")

        with pytest.raises(RuntimeError, match="System error"):
            service.get_session_summary("session-123", "player-456")

    def test_get_game_statistics_success(self, service):
        """Test get_game_statistics success (lines 353, 357-363)."""
        mock_stats = {
            "total_sessions": 10,
            "total_players": 25,
            "total_buy_ins": 50000,
            "total_cash_outs": 48000
        }
        service._domain_service.calculate_game_statistics.return_value = mock_stats

        result = service.get_game_statistics("ABC123")

        assert result == mock_stats
        service._domain_service.calculate_game_statistics.assert_called_once_with("ABC123")

    def test_get_game_statistics_repository_error(self, service):
        """Test get_game_statistics with repository error (lines 367-373)."""
        service._domain_service.calculate_game_statistics.side_effect = RepositoryError("Database error")

        with pytest.raises(Exception, match="Error fetching game statistics"):
            service.get_game_statistics("ABC123")

    def test_get_game_statistics_generic_error(self, service):
        """Test get_game_statistics with generic error (lines 367-373)."""
        service._domain_service.calculate_game_statistics.side_effect = RuntimeError("System error")

        with pytest.raises(RuntimeError, match="System error"):
            service.get_game_statistics("ABC123")

    def test_private_methods_implementation(self, service):
        """Test private methods actual implementation (lines 377-402, 407-414)."""
        with patch('src.services.ledger_service_v2.logger') as mock_logger:
            # Test _delete_orphaned_session
            service._delete_orphaned_session("session-123")
            mock_logger.info.assert_called()

            # Test _delete_session_model
            service._delete_session_model("session-123", "game-789")

            # Test _update_payment_balances_after_deletion
            service._update_payment_balances_after_deletion("game-789", "player-456")

            # Test _invalidate_game_cache
            service._invalidate_game_cache("game-789")

    def test_legacy_functions_with_parameters(self):
        """Test legacy functions with all parameter combinations (lines 453-454)."""
        # Import the legacy functions
        from src.services.ledger_service_v2 import get_session_summary

        with patch.object(LedgerService, '__enter__') as mock_enter, \
             patch.object(LedgerService, '__exit__') as mock_exit:

            mock_service = Mock()
            mock_enter.return_value = mock_service
            mock_service.get_session_summary.return_value = {"test": "result"}

            # Test with both parameters (the actual signature)
            result = get_session_summary("session-123", "player-456")

            assert result == {"test": "result"}
            mock_service.get_session_summary.assert_called_once_with("session-123", "player-456")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])