"""
SQLAlchemy implementation of the GameRepository.

This module provides concrete implementation of the repository interface,
mapping between domain entities and SQLAlchemy models for game operations.
"""

from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from domain.game.repositories import GameRepository
from domain.game.entities import Game
from domain.poker.value_objects import GameId, PublicCode, AdminToken, GameTitle
from domain.poker.exceptions import (
    GameNotFoundError,
    DuplicatePublicCodeError,
    DuplicateAdminTokenError,
    RepositoryError
)
from db.models import Game as GameModel


class SQLAlchemyGameRepository(GameRepository):
    """
    SQLAlchemy implementation of GameRepository.

    This repository maps between domain entities (Game) and
    SQLAlchemy models (Game) in the existing database.
    """

    def __init__(self, db_session: Session) -> None:
        """
        Initialize the repository with a database session.

        Args:
            db_session: SQLAlchemy database session
        """
        self._db_session = db_session

    def save(self, game: Game) -> Game:
        """
        Save a game entity to persistent storage.

        Args:
            game: The Game entity to save

        Returns:
            The saved Game entity

        Raises:
            DuplicatePublicCodeError: If public code already exists
            DuplicateAdminTokenError: If admin token already exists
            RepositoryError: For other persistence errors
        """
        try:
            # Convert domain entity to SQLAlchemy model
            db_game = self._to_db_model(game)

            self._db_session.add(db_game)
            self._db_session.flush()  # Flush to get constraint violations
            # Note: Caller is responsible for commit

            # Return the domain entity (unchanged since we have all data)
            return game

        except IntegrityError as e:
            error_msg = str(e.orig).lower() if hasattr(e, 'orig') else str(e).lower()

            if 'public_code' in error_msg:
                raise DuplicatePublicCodeError(str(game.public_code))
            elif 'admin_code' in error_msg:
                raise DuplicateAdminTokenError()
            else:
                raise RepositoryError("save", f"Integrity constraint violation: {str(e)}")

        except SQLAlchemyError as e:
            raise RepositoryError("save", str(e))

    def get_by_id(self, game_id: GameId) -> Optional[Game]:
        """
        Retrieve a game by its unique identifier.

        Args:
            game_id: The unique game identifier

        Returns:
            The Game entity if found, None otherwise
        """
        try:
            db_game = self._db_session.query(GameModel).filter(
                GameModel.id == game_id.value
            ).first()

            if db_game is None:
                return None

            return self._to_domain_entity(db_game)

        except SQLAlchemyError as e:
            raise RepositoryError("get_by_id", str(e))

    def get_by_public_code(self, public_code: PublicCode) -> Optional[Game]:
        """
        Retrieve a game by its public code.

        Args:
            public_code: The public sharing code

        Returns:
            The Game entity if found, None otherwise
        """
        try:
            db_game = self._db_session.query(GameModel).filter(
                GameModel.public_code == str(public_code)
            ).first()

            if db_game is None:
                return None

            return self._to_domain_entity(db_game)

        except SQLAlchemyError as e:
            raise RepositoryError("get_by_public_code", str(e))

    def get_by_admin_token(self, admin_token: AdminToken) -> Optional[Game]:
        """
        Retrieve a game by its admin token.

        Args:
            admin_token: The administrative access token

        Returns:
            The Game entity if found, None otherwise
        """
        try:
            db_game = self._db_session.query(GameModel).filter(
                GameModel.admin_code == admin_token.value
            ).first()

            if db_game is None:
                return None

            return self._to_domain_entity(db_game)

        except SQLAlchemyError as e:
            raise RepositoryError("get_by_admin_token", str(e))

    def public_code_exists(self, public_code: PublicCode) -> bool:
        """
        Check if a public code is already in use.

        Args:
            public_code: The public code to check

        Returns:
            True if the code exists, False otherwise
        """
        try:
            count = self._db_session.query(GameModel).filter(
                GameModel.public_code == str(public_code)
            ).count()

            return count > 0

        except SQLAlchemyError as e:
            raise RepositoryError("public_code_exists", str(e))

    def admin_token_exists(self, admin_token: AdminToken) -> bool:
        """
        Check if an admin token is already in use.

        Args:
            admin_token: The admin token to check

        Returns:
            True if the token exists, False otherwise
        """
        try:
            count = self._db_session.query(GameModel).filter(
                GameModel.admin_code == admin_token.value
            ).count()

            return count > 0

        except SQLAlchemyError as e:
            raise RepositoryError("admin_token_exists", str(e))

    def update(self, game: Game) -> Game:
        """
        Update an existing game entity.

        Args:
            game: The Game entity with updated data

        Returns:
            The updated Game entity

        Raises:
            GameNotFoundError: If the game doesn't exist
            RepositoryError: For other persistence errors
        """
        try:
            db_game = self._db_session.query(GameModel).filter(
                GameModel.id == game.id.value
            ).first()

            if db_game is None:
                raise GameNotFoundError(str(game.id), "ID")

            # Update the model with new data
            db_game.title = str(game.title) if game.title else None
            db_game.meta = game.metadata
            # Note: public_code and admin_code typically shouldn't change

            self._db_session.flush()
            # Note: Caller is responsible for commit

            return game

        except GameNotFoundError:
            raise
        except SQLAlchemyError as e:
            raise RepositoryError("update", str(e))

    def delete(self, game_id: GameId) -> bool:
        """
        Delete a game and all related data.

        Args:
            game_id: The unique game identifier

        Returns:
            True if the game was deleted, False if it didn't exist

        Raises:
            RepositoryError: For persistence errors during deletion
        """
        try:
            db_game = self._db_session.query(GameModel).filter(
                GameModel.id == game_id.value
            ).first()

            if db_game is None:
                return False

            self._db_session.delete(db_game)
            self._db_session.flush()
            # Note: Caller is responsible for commit

            return True

        except SQLAlchemyError as e:
            raise RepositoryError("delete", str(e))

    def _to_db_model(self, game: Game) -> GameModel:
        """
        Convert a domain Game entity to a SQLAlchemy model.

        Args:
            game: The domain entity

        Returns:
            SQLAlchemy Game model
        """
        return GameModel(
            id=game.id.value,
            public_code=str(game.public_code),
            admin_code=game.admin_token.value,
            title=str(game.title) if game.title else None,
            created_at=game.created_at,
            meta=game.metadata
        )

    def _to_domain_entity(self, db_game: GameModel) -> Game:
        """
        Convert a SQLAlchemy model to a domain Game entity.

        Args:
            db_game: The SQLAlchemy model

        Returns:
            Domain Game entity
        """
        return Game(
            id=GameId(str(db_game.id)),
            public_code=PublicCode(db_game.public_code),
            admin_token=AdminToken(db_game.admin_code),
            title=GameTitle(db_game.title) if db_game.title else None,
            created_at=db_game.created_at,
            metadata=db_game.meta or {}
        )