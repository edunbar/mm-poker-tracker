"""Simple error tests for game_creation_service_v2 to reach 90% coverage."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pytest
from unittest.mock import Mock, patch, MagicMock
import uuid

# Import for coverage
import src.services.game_creation_service_v2
from src.services.game_creation_service_v2 import GameCreationService
from src.domain.poker.exceptions import (
    DuplicatePublicCodeError,
    DuplicateAdminTokenError,
    GameCreationError,
    RepositoryError
)


class TestGameCreationSimpleErrors:
    """Simple error tests to reach the missing lines."""

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

    def test_duplicate_public_code_error_simple(self, service):
        """Test DuplicatePublicCodeError exception (lines 97-98)."""
        service._domain_service.create_game.side_effect = DuplicatePublicCodeError()

        with pytest.raises(RuntimeError, match="Failed to create game due to database constraints"):
            service.create_game("Test")

    def test_duplicate_admin_token_error_simple(self, service):
        """Test DuplicateAdminTokenError exception (lines 97-98)."""
        service._domain_service.create_game.side_effect = DuplicateAdminTokenError()

        with pytest.raises(RuntimeError, match="Failed to create game due to database constraints"):
            service.create_game("Test")

    def test_game_creation_error_simple(self, service):
        """Test GameCreationError exception (lines 102-103)."""
        service._domain_service.create_game.side_effect = GameCreationError("Failed")

        with pytest.raises(RuntimeError, match="Failed"):
            service.create_game("Test")

    def test_repository_error_simple(self, service):
        """Test RepositoryError exception (lines 107-108)."""
        service._domain_service.create_game.side_effect = RepositoryError("Database error")

        with pytest.raises(RuntimeError, match="Failed to create game: Database error"):
            service.create_game("Test")

    def test_get_public_code_repository_error_simple(self, service):
        """Test repository error in get_by_public_code (lines 162-164)."""
        service._repository.get_by_public_code.side_effect = RepositoryError("Database error")

        result = service.get_game_by_public_code("ABCDE")

        assert result is None

    def test_get_admin_token_repository_error_simple(self, service):
        """Test repository error in get_by_admin_token (lines 186-188)."""
        service._repository.get_by_admin_token.side_effect = RepositoryError("Database error")

        result = service.get_game_by_admin_token("admin-token-123456789012345678901234567890")

        assert result is None

    def test_update_game_not_found_simple(self, service):
        """Test update when game not found (line 210)."""
        service._repository.get_by_id.return_value = None

        # Use a proper UUID
        game_id = str(uuid.uuid4())
        result = service.update_game_title(game_id, "New Title")

        assert result is False

    def test_update_repository_error_simple(self, service):
        """Test repository error in update (lines 229-231)."""
        mock_game = Mock()
        service._repository.get_by_id.return_value = mock_game

        mock_title = Mock()
        service._domain_service.validate_title.return_value = mock_title

        updated_game = Mock()
        mock_game.update_title.return_value = updated_game

        service._repository.update.side_effect = RepositoryError("Database error")

        # Use a proper UUID
        game_id = str(uuid.uuid4())
        with pytest.raises(RuntimeError, match="Failed to update game: Database error"):
            service.update_game_title(game_id, "New Title")

    def test_update_unexpected_error_simple(self, service):
        """Test unexpected error in update (lines 233-235)."""
        mock_game = Mock()
        service._repository.get_by_id.return_value = mock_game

        mock_title = Mock()
        service._domain_service.validate_title.return_value = mock_title

        updated_game = Mock()
        mock_game.update_title.return_value = updated_game

        service._repository.update.side_effect = ConnectionError("Network error")

        # Use a proper UUID
        game_id = str(uuid.uuid4())
        with pytest.raises(RuntimeError, match="Failed to update game: Network error"):
            service.update_game_title(game_id, "New Title")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])