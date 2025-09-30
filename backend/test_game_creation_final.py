"""Final tests to push game_creation_service_v2 to 90%+ coverage."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pytest
from unittest.mock import Mock, patch, MagicMock
import uuid

# Import for coverage
import src.services.game_creation_service_v2
from src.services.game_creation_service_v2 import GameCreationService, create_game, validate_game_title
from src.domain.poker.value_objects import GameId
from src.domain.poker.exceptions import (
    DuplicatePublicCodeError,
    DuplicateAdminTokenError,
    GameCreationError,
    RepositoryError
)


class TestGameCreationServiceFinal:
    """Final tests to reach 90%+ coverage targeting specific missing lines."""

    @pytest.fixture
    def service(self):
        """Create service with mocked dependencies."""
        mock_session = Mock()
        with patch('src.services.game_creation_service_v2.SQLAlchemyGameRepository') as mock_repo_class, \
             patch('src.services.game_creation_service_v2.DomainGameCreationService') as mock_domain_class:

            mock_repo = Mock()
            mock_domain = Mock()
            mock_repo_class.return_value = mock_repo
            mock_domain_class.return_value = mock_domain

            service = GameCreationService(mock_session)
            service._repository = mock_repo
            service._domain_service = mock_domain
            return service

    def test_create_game_duplicate_public_code_logged(self, service):
        """Test DuplicatePublicCodeError is caught and logged (lines 97-98)."""
        with patch('src.services.game_creation_service_v2.logger') as mock_logger:
            service._domain_service.create_game.side_effect = DuplicatePublicCodeError("ABCDE")

            with pytest.raises(RuntimeError):
                service.create_game("Test Game")

            # Verify error was logged
            mock_logger.error.assert_called_once()

    def test_create_game_duplicate_admin_token_logged(self, service):
        """Test DuplicateAdminTokenError is caught and logged (lines 97-98)."""
        with patch('src.services.game_creation_service_v2.logger') as mock_logger:
            service._domain_service.create_game.side_effect = DuplicateAdminTokenError("token")

            with pytest.raises(RuntimeError):
                service.create_game("Test Game")

            # Verify error was logged
            mock_logger.error.assert_called_once()

    def test_create_game_creation_error_logged(self, service):
        """Test GameCreationError is caught and logged (lines 102-103)."""
        with patch('src.services.game_creation_service_v2.logger') as mock_logger:
            service._domain_service.create_game.side_effect = GameCreationError("Creation failed")

            with pytest.raises(RuntimeError):
                service.create_game("Test Game")

            # Verify error was logged
            mock_logger.error.assert_called_once()

    def test_create_game_repository_error_logged(self, service):
        """Test RepositoryError is caught and logged (lines 107-108)."""
        with patch('src.services.game_creation_service_v2.logger') as mock_logger:
            service._domain_service.create_game.side_effect = RepositoryError("Database error")

            with pytest.raises(RuntimeError):
                service.create_game("Test Game")

            # Verify error was logged
            mock_logger.error.assert_called_once()

    def test_get_public_code_repository_error_logged(self, service):
        """Test repository error in get_by_public_code is caught and logged (lines 162-164)."""
        with patch('src.services.game_creation_service_v2.logger') as mock_logger:
            service._repository.get_by_public_code.side_effect = RepositoryError("Database error")

            result = service.get_game_by_public_code("ABCDE")

            assert result is None
            # Verify error was logged
            mock_logger.error.assert_called_once()

    def test_get_admin_token_repository_error_logged(self, service):
        """Test repository error in get_by_admin_token is caught and logged (lines 186-188)."""
        with patch('src.services.game_creation_service_v2.logger') as mock_logger:
            service._repository.get_by_admin_token.side_effect = RepositoryError("Database error")

            result = service.get_game_by_admin_token("admin-token-123456789012345678901234567890")

            assert result is None
            # Verify error was logged
            mock_logger.error.assert_called_once()

    def test_update_game_title_full_path(self, service):
        """Test complete update_game_title path (lines 205-235)."""
        # Create mock game
        mock_game = Mock()
        mock_game.id = GameId(str(uuid.uuid4()))
        service._repository.get_by_id.return_value = mock_game

        # Mock title validation
        mock_title = Mock()
        service._domain_service.validate_title.return_value = mock_title

        # Mock game update
        updated_game = Mock()
        mock_game.update_title.return_value = updated_game

        # Test the full execution path
        result = service.update_game_title(str(mock_game.id), "New Title")

        # Verify all steps executed
        assert result is True
        service._repository.get_by_id.assert_called_once()
        service._domain_service.validate_title.assert_called_once_with("New Title")
        mock_game.update_title.assert_called_once_with(mock_title)
        service._repository.update.assert_called_once_with(updated_game)

    def test_update_game_title_not_found_path(self, service):
        """Test update when game not found (lines 209-210)."""
        service._repository.get_by_id.return_value = None

        result = service.update_game_title("nonexistent-id", "New Title")

        assert result is False

    def test_update_game_title_none_title_path(self, service):
        """Test update with None title doesn't call validation (lines 213-216)."""
        mock_game = Mock()
        service._repository.get_by_id.return_value = mock_game

        updated_game = Mock()
        mock_game.update_title.return_value = updated_game

        result = service.update_game_title("game-id", None)

        assert result is True
        # Should not call validate_title for None
        service._domain_service.validate_title.assert_not_called()
        mock_game.update_title.assert_called_once_with(None)

    def test_update_game_title_validation_error_logged(self, service):
        """Test validation error is logged and re-raised (lines 225-227)."""
        mock_game = Mock()
        service._repository.get_by_id.return_value = mock_game
        service._domain_service.validate_title.side_effect = ValueError("Title too long")

        with patch('src.services.game_creation_service_v2.logger') as mock_logger:
            with pytest.raises(ValueError):
                service.update_game_title("game-id", "Very long title")

            # Verify error was logged
            mock_logger.error.assert_called_once()

    def test_update_game_title_repository_error_logged(self, service):
        """Test repository error is logged and converted (lines 229-231)."""
        mock_game = Mock()
        service._repository.get_by_id.return_value = mock_game
        mock_title = Mock()
        service._domain_service.validate_title.return_value = mock_title

        updated_game = Mock()
        mock_game.update_title.return_value = updated_game
        service._repository.update.side_effect = RepositoryError("Database error")

        with patch('src.services.game_creation_service_v2.logger') as mock_logger:
            with pytest.raises(RuntimeError):
                service.update_game_title("game-id", "New Title")

            # Verify error was logged
            mock_logger.error.assert_called_once()

    def test_update_game_title_unexpected_error_logged(self, service):
        """Test unexpected error is logged and converted (lines 233-235)."""
        mock_game = Mock()
        service._repository.get_by_id.return_value = mock_game
        mock_title = Mock()
        service._domain_service.validate_title.return_value = mock_title

        updated_game = Mock()
        mock_game.update_title.return_value = updated_game
        service._repository.update.side_effect = ConnectionError("Network error")

        with patch('src.services.game_creation_service_v2.logger') as mock_logger:
            with pytest.raises(RuntimeError):
                service.update_game_title("game-id", "New Title")

            # Verify error was logged with exception details
            mock_logger.exception.assert_called_once_with("Unexpected error updating game title")

    def test_legacy_create_game_function_executes(self):
        """Test legacy create_game function calls service (lines 277-278)."""
        with patch.object(GameCreationService, '__enter__') as mock_enter, \
             patch.object(GameCreationService, '__exit__') as mock_exit:

            mock_service = Mock()
            mock_enter.return_value = mock_service
            mock_service.create_game.return_value = {"test": "result"}

            result = create_game("Test Title")

            assert result == {"test": "result"}
            mock_service.create_game.assert_called_once_with(title="Test Title")

    def test_legacy_validate_game_title_function_executes(self):
        """Test legacy validate_game_title function calls service (lines 296-297)."""
        with patch.object(GameCreationService, '__enter__') as mock_enter, \
             patch.object(GameCreationService, '__exit__') as mock_exit:

            mock_service = Mock()
            mock_enter.return_value = mock_service
            mock_service.validate_game_title.return_value = "Valid Title"

            result = validate_game_title("Test Title")

            assert result == "Valid Title"
            mock_service.validate_game_title.assert_called_once_with("Test Title")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])