"""Focused tests for game_creation_service_v2 to achieve 90%+ coverage."""

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
from src.domain.poker.value_objects import GameId, PublicCode, AdminToken, GameTitle
from src.domain.poker.exceptions import (
    GameCreationError,
    DuplicatePublicCodeError,
    DuplicateAdminTokenError,
    RepositoryError
)


class TestGameCreationServiceFocused:
    """Focused tests targeting missing coverage areas with mock entities."""

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
    def mock_game(self):
        """Create a mock game entity."""
        game = Mock()
        game.id = GameId(str(uuid.uuid4()))
        game.public_code = PublicCode("ABCDE")
        game.admin_token = AdminToken("admin-token-123456789012345678901234567890")
        game.title = GameTitle("Test Game")
        game.created_at = datetime.now(timezone.utc)
        return game

    def test_create_game_success_calls_to_legacy_format(self, service, mock_game):
        """Test create_game calls _to_legacy_format (covers line 88)."""
        service._domain_service.create_game.return_value = mock_game

        # Mock the _to_legacy_format method to track it was called
        with patch.object(service, '_to_legacy_format', return_value={"test": "result"}) as mock_format:
            result = service.create_game("Test Game")

            service._domain_service.create_game.assert_called_once_with(title="Test Game")
            mock_format.assert_called_once_with(mock_game)
            assert result == {"test": "result"}

    def test_create_game_duplicate_public_code_error(self, service):
        """Test DuplicatePublicCodeError handling (covers lines 97-98)."""
        service._domain_service.create_game.side_effect = DuplicatePublicCodeError("ABCDE")

        with pytest.raises(RuntimeError, match="Failed to create game due to database constraints"):
            service.create_game("Test Game")

    def test_create_game_duplicate_admin_token_error(self, service):
        """Test DuplicateAdminTokenError handling (covers lines 97-98)."""
        service._domain_service.create_game.side_effect = DuplicateAdminTokenError("token")

        with pytest.raises(RuntimeError, match="Failed to create game due to database constraints"):
            service.create_game("Test Game")

    def test_create_game_creation_error(self, service):
        """Test GameCreationError handling (covers lines 102-103)."""
        service._domain_service.create_game.side_effect = GameCreationError("Creation failed")

        with pytest.raises(RuntimeError, match="Creation failed"):
            service.create_game("Test Game")

    def test_create_game_repository_error(self, service):
        """Test RepositoryError handling (covers lines 107-108)."""
        service._domain_service.create_game.side_effect = RepositoryError("Database error")

        with pytest.raises(RuntimeError, match="Failed to create game: Database error"):
            service.create_game("Test Game")

    def test_validate_game_title_returns_validated(self, service):
        """Test validate_game_title returns string from validated title (covers lines 128-139)."""
        mock_title = Mock()
        mock_title.__str__ = Mock(return_value="Validated Title")
        service._domain_service.validate_title.return_value = mock_title

        result = service.validate_game_title("Title")

        service._domain_service.validate_title.assert_called_once_with("Title")
        assert result == "Validated Title"

    def test_validate_game_title_returns_none(self, service):
        """Test validate_game_title with None result (covers lines 132-134)."""
        service._domain_service.validate_title.return_value = None

        result = service.validate_game_title("Title")

        assert result is None

    def test_get_game_by_public_code_success(self, service, mock_game):
        """Test successful public code lookup (covers lines 154-156)."""
        service._repository.get_by_public_code.return_value = mock_game

        result = service.get_game_by_public_code("ABCDE")

        assert result == mock_game
        service._repository.get_by_public_code.assert_called_once()

    def test_get_game_by_public_code_invalid_code(self, service):
        """Test invalid public code handling (covers lines 159-160)."""
        with patch('src.services.game_creation_service_v2.PublicCode') as mock_pc:
            mock_pc.side_effect = ValueError("Invalid code")

            result = service.get_game_by_public_code("INVALID")

            assert result is None

    def test_get_game_by_public_code_repository_error(self, service):
        """Test repository error handling (covers lines 163-164)."""
        service._repository.get_by_public_code.side_effect = RepositoryError("DB error")

        result = service.get_game_by_public_code("ABCDE")

        assert result is None

    def test_get_game_by_admin_token_success(self, service, mock_game):
        """Test successful admin token lookup."""
        service._repository.get_by_admin_token.return_value = mock_game

        result = service.get_game_by_admin_token("admin-token-123456789012345678901234567890")

        assert result == mock_game

    def test_get_game_by_admin_token_invalid_token(self, service):
        """Test invalid admin token handling (covers lines 187-188)."""
        with patch('src.services.game_creation_service_v2.AdminToken') as mock_at:
            mock_at.side_effect = ValueError("Invalid token")

            result = service.get_game_by_admin_token("INVALID")

            assert result is None

    def test_update_game_title_game_found(self, service, mock_game):
        """Test update title when game found (covers lines 205-235)."""
        # Setup repository to return game
        service._repository.get_by_id.return_value = mock_game

        # Setup title validation
        mock_title = Mock()
        service._domain_service.validate_title.return_value = mock_title

        # Setup game update
        updated_game = Mock()
        mock_game.update_title = Mock(return_value=updated_game)

        result = service.update_game_title("game-id", "New Title")

        assert result is True
        service._repository.get_by_id.assert_called_once()
        service._domain_service.validate_title.assert_called_once_with("New Title")
        mock_game.update_title.assert_called_once_with(mock_title)
        service._repository.update.assert_called_once_with(updated_game)

    def test_update_game_title_game_not_found(self, service):
        """Test update title when game not found (covers lines 209-210)."""
        service._repository.get_by_id.return_value = None

        result = service.update_game_title("game-id", "New Title")

        assert result is False

    def test_update_game_title_with_none_title(self, service, mock_game):
        """Test update with None title (covers lines 213-216)."""
        service._repository.get_by_id.return_value = mock_game
        service._domain_service.validate_title.return_value = None

        updated_game = Mock()
        mock_game.update_title = Mock(return_value=updated_game)

        result = service.update_game_title("game-id", None)

        assert result is True
        # Should not call validate_title for None
        service._domain_service.validate_title.assert_not_called()
        mock_game.update_title.assert_called_once_with(None)

    def test_update_game_title_validation_error(self, service, mock_game):
        """Test update with validation error (covers lines 225-227)."""
        service._repository.get_by_id.return_value = mock_game
        service._domain_service.validate_title.side_effect = ValueError("Title too long")

        with pytest.raises(ValueError, match="Title too long"):
            service.update_game_title("game-id", "Very long title")

    def test_update_game_title_repository_error(self, service, mock_game):
        """Test update with repository error (covers lines 229-231)."""
        service._repository.get_by_id.return_value = mock_game
        mock_title = Mock()
        service._domain_service.validate_title.return_value = mock_title

        updated_game = Mock()
        mock_game.update_title = Mock(return_value=updated_game)
        service._repository.update.side_effect = RepositoryError("DB error")

        with pytest.raises(RuntimeError, match="Failed to update game: DB error"):
            service.update_game_title("game-id", "New Title")

    def test_update_game_title_unexpected_error(self, service, mock_game):
        """Test update with unexpected error (covers lines 233-235)."""
        service._repository.get_by_id.return_value = mock_game
        mock_title = Mock()
        service._domain_service.validate_title.return_value = mock_title

        updated_game = Mock()
        mock_game.update_title = Mock(return_value=updated_game)
        service._repository.update.side_effect = ConnectionError("Network error")

        with pytest.raises(RuntimeError, match="Failed to update game: Network error"):
            service.update_game_title("game-id", "New Title")

    def test_to_legacy_format_direct(self, service, mock_game):
        """Test _to_legacy_format method directly (covers line 247)."""
        result = service._to_legacy_format(mock_game)

        expected_keys = ["game_id", "public_code", "admin_code", "title", "created_at"]
        for key in expected_keys:
            assert key in result

        assert result["game_id"] == str(mock_game.id)
        assert result["public_code"] == str(mock_game.public_code)
        assert result["admin_code"] == mock_game.admin_token.value
        assert result["title"] == str(mock_game.title)
        assert isinstance(result["created_at"], str)

    def test_to_legacy_format_none_title(self, service):
        """Test _to_legacy_format with None title."""
        mock_game = Mock()
        mock_game.id = GameId(str(uuid.uuid4()))
        mock_game.public_code = PublicCode("ABCDE")
        mock_game.admin_token = AdminToken("admin-token-123456789012345678901234567890")
        mock_game.title = None
        mock_game.created_at = datetime.now(timezone.utc)

        result = service._to_legacy_format(mock_game)

        assert result["title"] is None

    def test_legacy_create_game_function(self):
        """Test legacy create_game function (covers lines 277-278)."""
        with patch('src.services.game_creation_service_v2.GameCreationService') as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            expected = {"game_id": "test", "public_code": "TEST"}
            mock_service.create_game.return_value = expected

            result = create_game("Test")

            mock_service.create_game.assert_called_once_with(title="Test")
            assert result == expected

    def test_legacy_validate_game_title_function(self):
        """Test legacy validate_game_title function (covers lines 296-297)."""
        with patch('src.services.game_creation_service_v2.GameCreationService') as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            mock_service.validate_game_title.return_value = "Valid"

            result = validate_game_title("Valid")

            mock_service.validate_game_title.assert_called_once_with("Valid")
            assert result == "Valid"

    def test_context_manager_session_close(self):
        """Test context manager closes session (covers lines 56, 59-60)."""
        mock_session = Mock()

        with patch('src.services.game_creation_service_v2.SessionLocal', return_value=mock_session), \
             patch('src.services.game_creation_service_v2.SQLAlchemyGameRepository'), \
             patch('src.services.game_creation_service_v2.DomainGameCreationService'):

            with GameCreationService() as service:
                assert service._should_close_session is True

            mock_session.close.assert_called_once()

    def test_init_without_session_creates_session(self):
        """Test init without session creates new one (covers line 50)."""
        mock_session = Mock()

        with patch('src.services.game_creation_service_v2.SessionLocal', return_value=mock_session), \
             patch('src.services.game_creation_service_v2.SQLAlchemyGameRepository'), \
             patch('src.services.game_creation_service_v2.DomainGameCreationService'):

            service = GameCreationService()
            assert service._db_session == mock_session
            assert service._should_close_session is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])