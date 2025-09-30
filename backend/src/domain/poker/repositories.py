"""
Repository interfaces for the poker domain.

Repositories define the contract for persistence operations without specifying
the actual implementation. This allows the domain layer to be independent
of infrastructure concerns while still defining its persistence needs.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from .entities.poker_session import PokerSession
from .value_objects import SessionId, PlayerId, GameId


class PokerSessionRepository(ABC):
    """
    Abstract repository interface for PokerSession entities.

    This interface defines all the persistence operations needed by the domain
    without specifying how they are implemented (database, file system, etc.).
    """

    @abstractmethod
    def save(self, session: PokerSession) -> None:
        """
        Save a poker session.

        Args:
            session: The session to save

        Raises:
            RepositoryError: If the save operation fails
        """
        pass

    @abstractmethod
    def find_by_id(self, session_id: SessionId) -> Optional[PokerSession]:
        """
        Find a session by its ID.

        Args:
            session_id: The session ID to search for

        Returns:
            The session if found, None otherwise

        Raises:
            RepositoryError: If the query operation fails
        """
        pass

    @abstractmethod
    def find_by_player_id(self, player_id: PlayerId) -> List[PokerSession]:
        """
        Find all sessions for a specific player.

        Args:
            player_id: The player ID to search for

        Returns:
            List of sessions for the player (may be empty)

        Raises:
            RepositoryError: If the query operation fails
        """
        pass

    @abstractmethod
    def find_by_game_id(self, game_id: GameId) -> List[PokerSession]:
        """
        Find all sessions for a specific game.

        Args:
            game_id: The game ID to search for

        Returns:
            List of sessions for the game (may be empty)

        Raises:
            RepositoryError: If the query operation fails
        """
        pass

    @abstractmethod
    def find_active_sessions(self) -> List[PokerSession]:
        """
        Find all currently active sessions.

        Returns:
            List of active sessions (may be empty)

        Raises:
            RepositoryError: If the query operation fails
        """
        pass

    @abstractmethod
    def find_active_sessions_for_player(self, player_id: PlayerId) -> List[PokerSession]:
        """
        Find all active sessions for a specific player.

        Args:
            player_id: The player ID to search for

        Returns:
            List of active sessions for the player (may be empty)

        Raises:
            RepositoryError: If the query operation fails
        """
        pass

    @abstractmethod
    def find_sessions_by_game_and_player(
        self, game_id: GameId, player_id: PlayerId
    ) -> List[PokerSession]:
        """
        Find all sessions for a specific game and player combination.

        Args:
            game_id: The game ID to search for
            player_id: The player ID to search for

        Returns:
            List of sessions for the game and player (may be empty)

        Raises:
            RepositoryError: If the query operation fails
        """
        pass

    @abstractmethod
    def delete(self, session_id: SessionId) -> bool:
        """
        Delete a session.

        Args:
            session_id: The session ID to delete

        Returns:
            True if session was deleted, False if not found

        Raises:
            RepositoryError: If the delete operation fails
        """
        pass

    @abstractmethod
    def exists(self, session_id: SessionId) -> bool:
        """
        Check if a session exists.

        Args:
            session_id: The session ID to check

        Returns:
            True if session exists, False otherwise

        Raises:
            RepositoryError: If the query operation fails
        """
        pass

    @abstractmethod
    def count_by_player(self, player_id: PlayerId) -> int:
        """
        Count sessions for a specific player.

        Args:
            player_id: The player ID to count sessions for

        Returns:
            Number of sessions for the player

        Raises:
            RepositoryError: If the query operation fails
        """
        pass

    @abstractmethod
    def count_by_game(self, game_id: GameId) -> int:
        """
        Count sessions for a specific game.

        Args:
            game_id: The game ID to count sessions for

        Returns:
            Number of sessions for the game

        Raises:
            RepositoryError: If the query operation fails
        """
        pass


class RepositoryError(Exception):
    """
    Base exception for repository operations.

    This allows the domain layer to handle persistence errors
    without coupling to specific infrastructure technologies.
    """

    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.original_error = original_error


class SessionNotFoundError(RepositoryError):
    """Raised when a requested session cannot be found."""

    def __init__(self, session_id: SessionId) -> None:
        super().__init__(f"Session with ID {session_id} was not found")
        self.session_id = session_id


class SessionAlreadyExistsError(RepositoryError):
    """Raised when attempting to save a session that already exists."""

    def __init__(self, session_id: SessionId) -> None:
        super().__init__(f"Session with ID {session_id} already exists")
        self.session_id = session_id


class RepositoryConnectionError(RepositoryError):
    """Raised when there are connectivity issues with the persistence layer."""

    def __init__(self, message: str = "Repository connection error") -> None:
        super().__init__(message)