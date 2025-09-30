"""
Domain-based GameCreationService v2

Direct replacement for game_creation_service.py using domain layer.
Maintains exact API compatibility while using clean domain architecture.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session as DBSession

from db.database import SessionLocal
from domain.game.entities import Game
from domain.game.services import GameCreationService as DomainGameCreationService
from domain.poker.value_objects import GameId, PublicCode, AdminToken, GameTitle
from domain.poker.exceptions import (
    GameCreationError,
    DuplicatePublicCodeError,
    DuplicateAdminTokenError,
    RepositoryError
)
from infrastructure.persistence.sqlalchemy.game_repository import SQLAlchemyGameRepository

logger = logging.getLogger(__name__)


class GameCreationService:
    """
    Domain-based GameCreationService that replaces the old function-based approach.

    Uses domain entities and repositories for game creation while maintaining
    exact API compatibility with existing Flask routes.
    """

    def __init__(self, db_session: DBSession):
        """
        Initialize with required database session.

        Args:
            db_session: SQLAlchemy session (REQUIRED). Session lifecycle is managed
                       by the caller (typically the web layer).

        Raises:
            ValueError: If db_session is None
        """
        if db_session is None:
            raise ValueError("db_session is required - services do not manage sessions")

        self._db_session = db_session
        self._repository = SQLAlchemyGameRepository(self._db_session)
        self._domain_service = DomainGameCreationService(self._repository)

    def create_game(self, title: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new game with generated codes - maintains compatibility with legacy service.

        Args:
            title: Optional title for the game

        Returns:
            Dictionary with game details in legacy format:
            {
                "game_id": "uuid",
                "public_code": "ABC123",
                "admin_code": "long-secret-token",
                "title": "My Poker Game",
                "created_at": "2025-01-15T10:30:00Z"
            }

        Raises:
            ValueError: If title validation fails
            RuntimeError: If game creation fails
        """
        try:
            # Use domain service to create game
            game = self._domain_service.create_game(title=title)

            # Convert domain entity to legacy format
            return self._to_legacy_format(game)

        except ValueError as e:
            # Re-raise validation errors as-is for compatibility
            logger.error(f"Game creation validation error: {e}")
            raise

        except (DuplicatePublicCodeError, DuplicateAdminTokenError) as e:
            # Convert domain exceptions to RuntimeError for compatibility
            logger.error(f"Game creation failed due to duplicate codes: {e}")
            raise RuntimeError("Failed to create game due to database constraints")

        except GameCreationError as e:
            # Convert domain exception to RuntimeError for compatibility
            logger.error(f"Game creation failed: {e}")
            raise RuntimeError(str(e))

        except RepositoryError as e:
            # Convert repository errors to RuntimeError for compatibility
            logger.error(f"Repository error during game creation: {e}")
            raise RuntimeError(f"Failed to create game: {str(e)}")

        except Exception as e:
            # Catch-all for unexpected errors
            logger.exception("Unexpected error during game creation")
            raise RuntimeError(f"Failed to create game: {str(e)}")

    def validate_game_title(self, title: str) -> str:
        """
        Validate game title input - maintains compatibility with legacy service.

        Args:
            title: The title to validate

        Returns:
            The validated and cleaned title

        Raises:
            ValueError: If title is invalid
        """
        try:
            # Use domain service for validation
            validated_title = self._domain_service.validate_title(title)

            if validated_title is None:
                return None

            return str(validated_title)

        except ValueError as e:
            # Re-raise with legacy error format
            raise ValueError(str(e))

    def get_game_by_public_code(self, public_code: str) -> Optional[Game]:
        """
        Get a game entity by public code.

        This method is unique to the v2 service and provides access to the
        rich domain model for consumers that want to work with domain objects.

        Args:
            public_code: The game's public code

        Returns:
            Game domain object if found, None otherwise
        """
        try:
            public_code_vo = PublicCode(public_code)
            return self._repository.get_by_public_code(public_code_vo)

        except (TypeError, ValueError) as e:
            logger.warning(f"Invalid public code format: {public_code}, error: {e}")
            return None

        except RepositoryError as e:
            logger.error(f"Repository error getting game by public code: {e}")
            return None

    def get_game_by_admin_token(self, admin_token: str) -> Optional[Game]:
        """
        Get a game entity by admin token.

        This method is unique to the v2 service for admin operations.

        Args:
            admin_token: The game's admin token

        Returns:
            Game domain object if found, None otherwise
        """
        try:
            admin_token_vo = AdminToken(admin_token)
            return self._repository.get_by_admin_token(admin_token_vo)

        except (TypeError, ValueError) as e:
            logger.warning(f"Invalid admin token format, error: {e}")
            return None

        except RepositoryError as e:
            logger.error(f"Repository error getting game by admin token: {e}")
            return None

    def update_game_title(self, game_id: str, new_title: Optional[str]) -> bool:
        """
        Update a game's title.

        Args:
            game_id: The game's unique identifier
            new_title: The new title (None to remove title)

        Returns:
            True if update was successful, False if game not found

        Raises:
            ValueError: If title validation fails
            RuntimeError: If update operation fails
        """
        try:
            game_id_vo = GameId(game_id)
            game = self._repository.get_by_id(game_id_vo)

            if game is None:
                return False

            # Validate new title if provided
            title_vo = None
            if new_title is not None:
                title_vo = self._domain_service.validate_title(new_title)

            # Update game entity
            updated_game = game.update_title(title_vo)

            # Persist changes
            self._repository.update(updated_game)

            return True

        except ValueError as e:
            logger.error(f"Title validation error: {e}")
            raise

        except RepositoryError as e:
            logger.error(f"Repository error updating game: {e}")
            raise RuntimeError(f"Failed to update game: {str(e)}")

        except Exception as e:
            logger.exception("Unexpected error updating game title")
            raise RuntimeError(f"Failed to update game: {str(e)}")

    def _to_legacy_format(self, game: Game) -> Dict[str, Any]:
        """
        Convert domain Game entity to legacy API format.

        Args:
            game: The domain Game entity

        Returns:
            Dictionary in legacy format
        """
        return {
            "game_id": str(game.id),
            "public_code": str(game.public_code),
            "admin_code": game.admin_token.value,
            "title": str(game.title) if game.title else None,
            "created_at": game.created_at.isoformat()
        }


# =============================================================================
# Legacy Function-based API (for backward compatibility)
# =============================================================================

def create_game(title: Optional[str] = None) -> Dict[str, Any]:
    """
    Legacy function interface for game creation.

    Maintains backward compatibility with existing code that imports and calls
    this function directly.

    Args:
        title: Optional title for the game

    Returns:
        Dictionary with game details in legacy format

    Raises:
        ValueError: If title validation fails
        RuntimeError: If game creation fails
    """
    with SessionLocal() as db:
        try:
            service = GameCreationService(db)
            result = service.create_game(title=title)
            db.commit()
            return result
        except Exception:
            db.rollback()
            raise


def validate_game_title(title: str) -> str:
    """
    Legacy function interface for title validation.

    Maintains backward compatibility with existing code.

    Args:
        title: The title to validate

    Returns:
        The validated and cleaned title

    Raises:
        ValueError: If title is invalid
    """
    with SessionLocal() as db:
        service = GameCreationService(db)
        return service.validate_game_title(title)