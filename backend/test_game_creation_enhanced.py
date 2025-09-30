"""Enhanced tests for game_creation_service_v2 to achieve 90%+ coverage."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import uuid

# Import for coverage
import src.services.game_creation_service_v2
from src.services.game_creation_service_v2 import GameCreationService, create_game, validate_game_title
from src.domain.game.entities import Game
from src.domain.poker.value_objects import GameId, PublicCode, AdminToken, GameTitle
from src.domain.poker.exceptions import (
    GameCreationError,
    DuplicatePublicCodeError,
    DuplicateAdminTokenError,
    RepositoryError
)


class TestGameCreationServiceEnhanced:
    """Enhanced tests targeting missing coverage areas."""

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

    @pytest.fixture
    def sample_game(self):
        """Create a sample game entity for testing."""
        return Game(
            id=GameId(str(uuid.uuid4())),
            public_code=PublicCode("ABCDE"),
            admin_token=AdminToken("admin-token-123456789012345678901234567890"),
            title=GameTitle("Test Game"),
            created_at=datetime.now(timezone.utc)
        )

    def test_create_game_with_title_success(self, service, sample_game):
        """Test successful game creation with title - covers _to_legacy_format."""
        service._domain_service.create_game.return_value = sample_game

        result = service.create_game("Test Game")

        service._domain_service.create_game.assert_called_once_with(title="Test Game")

        # This tests the _to_legacy_format method (line 247)
        assert result["game_id"] == str(sample_game.id)
        assert result["public_code"] == "ABCDE"
        assert result["admin_code"] == "admin-token-123456789012345678901234567890"
        assert result["title"] == "Test Game"
        assert "created_at" in result

    def test_create_game_duplicate_errors(self, service):
        """Test duplicate error handling."""
        # Test DuplicatePublicCodeError (line 97-98)
        service._domain_service.create_game.side_effect = DuplicatePublicCodeError("ABCDE")

        with pytest.raises(RuntimeError, match="Failed to create game due to database constraints"):
            service.create_game("Test Game")

        # Test DuplicateAdminTokenError (line 97-98)
        service._domain_service.create_game.side_effect = DuplicateAdminTokenError("token")

        with pytest.raises(RuntimeError, match="Failed to create game due to database constraints"):
            service.create_game("Test Game")

    def test_create_game_errors(self, service):
        """Test various error scenarios."""
        # Test GameCreationError (line 102-103)
        service._domain_service.create_game.side_effect = GameCreationError("Creation failed")

        with pytest.raises(RuntimeError, match="Creation failed"):
            service.create_game("Test Game")

        # Test RepositoryError (line 107-108)
        service._domain_service.create_game.side_effect = RepositoryError("Database error")

        with pytest.raises(RuntimeError, match="Failed to create game: Database error"):
            service.create_game("Test Game")

    def test_get_game_by_public_code_success(self, service, sample_game):
        """Test successful game retrieval by public code."""
        service._repository.get_by_public_code.return_value = sample_game

        result = service.get_game_by_public_code("ABCDE")

        assert result == sample_game
        service._repository.get_by_public_code.assert_called_once()

    def test_get_game_by_public_code_invalid_format(self, service):
        """Test public code with invalid format."""
        # This should trigger the ValueError/TypeError handling (line 160)
        with patch('src.domain.poker.value_objects.PublicCode') as mock_public_code:
            mock_public_code.side_effect = ValueError("Invalid format")

            result = service.get_game_by_public_code("INVALID")

            assert result is None

    def test_get_game_by_public_code_repository_error(self, service):
        """Test repository error handling."""
        service._repository.get_by_public_code.side_effect = RepositoryError("Database error")

        result = service.get_game_by_public_code("ABCDE")

        assert result is None

    def test_get_game_by_admin_token_success(self, service, sample_game):
        """Test successful game retrieval by admin token."""
        service._repository.get_by_admin_token.return_value = sample_game

        result = service.get_game_by_admin_token("admin-token-123456789012345678901234567890")

        assert result == sample_game
        service._repository.get_by_admin_token.assert_called_once()

    def test_get_game_by_admin_token_invalid_format(self, service):
        """Test admin token with invalid format."""
        # This should trigger the ValueError/TypeError handling (line 186-188)
        with patch('src.domain.poker.value_objects.AdminToken') as mock_admin_token:
            mock_admin_token.side_effect = ValueError("Invalid format")

            result = service.get_game_by_admin_token("INVALID")

            assert result is None

    def test_get_game_by_admin_token_repository_error(self, service):
        """Test repository error handling for admin token."""
        service._repository.get_by_admin_token.side_effect = RepositoryError("Database error")

        result = service.get_game_by_admin_token("admin-token-123456789012345678901234567890")

        assert result is None

    def test_update_game_title_success(self, service, sample_game):
        """Test successful game title update."""
        # Mock getting the game
        service._repository.get_by_id.return_value = sample_game

        # Mock title validation
        mock_title = GameTitle("New Title")
        service._domain_service.validate_title.return_value = mock_title

        # Mock the game update method
        updated_game = Mock()
        sample_game.update_title = Mock(return_value=updated_game)

        result = service.update_game_title(str(sample_game.id), "New Title")

        assert result is True
        service._repository.get_by_id.assert_called_once()
        service._domain_service.validate_title.assert_called_once_with("New Title")
        sample_game.update_title.assert_called_once_with(mock_title)
        service._repository.update.assert_called_once_with(updated_game)

    def test_update_game_title_not_found(self, service):
        """Test game title update when game not found."""
        service._repository.get_by_id.return_value = None

        result = service.update_game_title(str(uuid.uuid4()), "New Title")

        assert result is False

    def test_update_game_title_with_none(self, service, sample_game):
        """Test game title update with None title."""
        service._repository.get_by_id.return_value = sample_game
        service._domain_service.validate_title.return_value = None

        updated_game = Mock()
        sample_game.update_title = Mock(return_value=updated_game)

        result = service.update_game_title(str(sample_game.id), None)

        assert result is True
        sample_game.update_title.assert_called_once_with(None)

    def test_update_game_title_validation_error(self, service, sample_game):
        """Test update with validation error."""
        service._repository.get_by_id.return_value = sample_game
        service._domain_service.validate_title.side_effect = ValueError("Title too long")

        with pytest.raises(ValueError, match="Title too long"):
            service.update_game_title(str(sample_game.id), "Very long title")

    def test_update_game_title_repository_error(self, service, sample_game):
        """Test update with repository error."""
        service._repository.get_by_id.return_value = sample_game
        mock_title = GameTitle("New Title")
        service._domain_service.validate_title.return_value = mock_title

        updated_game = Mock()
        sample_game.update_title = Mock(return_value=updated_game)
        service._repository.update.side_effect = RepositoryError("Database error")

        with pytest.raises(RuntimeError, match="Failed to update game: Database error"):
            service.update_game_title(str(sample_game.id), "New Title")

    def test_update_game_title_unexpected_error(self, service, sample_game):
        """Test update with unexpected error."""
        service._repository.get_by_id.return_value = sample_game
        mock_title = GameTitle("New Title")
        service._domain_service.validate_title.return_value = mock_title

        updated_game = Mock()
        sample_game.update_title = Mock(return_value=updated_game)
        service._repository.update.side_effect = ConnectionError("Network error")

        with pytest.raises(RuntimeError, match="Failed to update game: Network error"):
            service.update_game_title(str(sample_game.id), "New Title")

    def test_legacy_format_with_none_title(self, service):
        """Test legacy format conversion with None title."""
        game = Game(
            id=GameId(str(uuid.uuid4())),
            public_code=PublicCode("ABCDE"),
            admin_token=AdminToken("admin-token-123456789012345678901234567890"),
            title=None,
            created_at=datetime.now(timezone.utc)
        )

        result = service._to_legacy_format(game)

        assert result["title"] is None
        assert result["game_id"] == str(game.id)
        assert result["public_code"] == "ABCDE"

    def test_backward_compatibility_create_game(self):
        """Test backward compatibility create_game function."""
        with patch('src.services.game_creation_service_v2.GameCreationService') as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            expected_result = {
                "game_id": "test-id",
                "public_code": "ABCDE",
                "admin_code": "token-123456789012345678901234567890",
                "title": "Test Game",
                "created_at": "2025-01-15T10:30:00Z"
            }
            mock_service.create_game.return_value = expected_result

            result = create_game("Test Game")

            mock_service.create_game.assert_called_once_with(title="Test Game")
            assert result == expected_result

    def test_backward_compatibility_validate_title(self):
        """Test backward compatibility validate_game_title function."""
        with patch('src.services.game_creation_service_v2.GameCreationService') as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            mock_service.validate_game_title.return_value = "Valid Title"

            result = validate_game_title("Valid Title")

            mock_service.validate_game_title.assert_called_once_with("Valid Title")
            assert result == "Valid Title"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])