"""
Repository interfaces for the identity domain.

This module defines the contracts for user and poker identity claim persistence
operations without specifying the implementation (database, file system, etc.).

Note: For MVP, UserRepository methods return SQLAlchemy User models directly
rather than domain entities. This simplifies implementation while maintaining
clean separation between domain logic and infrastructure.

PokerIdentityClaimRepository works with domain entities for type safety.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict

from .entities import PokerIdentityClaim
from .value_objects import UserId
from ..poker.value_objects import PlayerId, GameId


class UserRepository(ABC):
    """
    Abstract repository interface for User persistence.

    This interface defines all user persistence operations needed by the domain
    without coupling to specific database technologies.

    Returns SQLAlchemy User models from db.models for MVP simplicity.
    """

    @abstractmethod
    def find_by_email(self, email: str) -> Optional:
        """
        Find a user by email address.

        Args:
            email: The user's email address (should be normalized/lowercased)

        Returns:
            SQLAlchemy User model if found, None otherwise

        Raises:
            RepositoryError: If the query operation fails
        """
        pass

    @abstractmethod
    def find_by_id(self, user_id: str) -> Optional:
        """
        Find a user by ID.

        Args:
            user_id: The user's UUID as a string

        Returns:
            SQLAlchemy User model if found, None otherwise

        Raises:
            RepositoryError: If the query operation fails
        """
        pass

    @abstractmethod
    def create(
        self,
        email: str,
        password_hash: str,
        display_name: str,
        email_verified: bool = False
    ):
        """
        Create a new user.

        Args:
            email: User's email address (should be normalized/lowercased)
            password_hash: Hashed password
            display_name: User's display name
            email_verified: Whether email is verified (default: False)

        Returns:
            Created SQLAlchemy User model

        Raises:
            RepositoryError: If the create operation fails
            IntegrityError: If email already exists
        """
        pass

    @abstractmethod
    def update(self, user):
        """
        Update an existing user.

        Args:
            user: SQLAlchemy User model with updated values

        Returns:
            Updated SQLAlchemy User model

        Raises:
            RepositoryError: If the update operation fails
        """
        pass


class PokerIdentityClaimRepository(ABC):
    """
    Abstract repository interface for PokerIdentityClaim persistence.

    This interface defines all poker identity claim persistence operations
    needed by the domain without coupling to specific database technologies.

    Works with domain entities (PokerIdentityClaim) for type safety.
    """

    @abstractmethod
    def get_by_id(self, claim_id: str) -> Optional[PokerIdentityClaim]:
        """
        Get a claim by its ID.

        Args:
            claim_id: The claim's UUID as a string

        Returns:
            PokerIdentityClaim if found, None otherwise

        Raises:
            RepositoryError: If the query operation fails
        """
        pass

    @abstractmethod
    def get_by_user_id(self, user_id: UserId) -> List[PokerIdentityClaim]:
        """
        Get all claims for a specific user.

        Args:
            user_id: The user's ID

        Returns:
            List of PokerIdentityClaim entities (may be empty)

        Raises:
            RepositoryError: If the query operation fails
        """
        pass

    @abstractmethod
    def get_by_player_id(self, player_id: PlayerId) -> Optional[PokerIdentityClaim]:
        """
        Get the claim for a specific player (if claimed).

        Args:
            player_id: The player's ID

        Returns:
            PokerIdentityClaim if the player is claimed, None otherwise

        Raises:
            RepositoryError: If the query operation fails
        """
        pass

    @abstractmethod
    def is_player_claimed(self, player_id: PlayerId) -> bool:
        """
        Check if a player has been claimed by a user.

        Args:
            player_id: The player's ID

        Returns:
            True if claimed, False otherwise

        Raises:
            RepositoryError: If the query operation fails
        """
        pass

    @abstractmethod
    def create(self, claim: PokerIdentityClaim) -> PokerIdentityClaim:
        """
        Create a new poker identity claim.

        Args:
            claim: The claim to create

        Returns:
            Created PokerIdentityClaim with populated ID

        Raises:
            IntegrityError: If the player is already claimed
            RepositoryError: If the create operation fails
        """
        pass

    @abstractmethod
    def delete(self, claim_id: str) -> bool:
        """
        Delete a claim by its ID.

        Args:
            claim_id: The claim's UUID as a string

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryError: If the delete operation fails
        """
        pass

    @abstractmethod
    def get_user_claims_with_details(self, user_id: UserId) -> List[Dict]:
        """
        Get all claims for a user with joined player and game data.

        Returns detailed information for each claimed player including
        which games they've participated in.

        Args:
            user_id: The user's ID

        Returns:
            List of dictionaries with claim, player, and game details:
            [
                {
                    'claim_id': str,
                    'player_id': str,
                    'player_name': str,
                    'claimed_at': datetime,
                    'verification_method': str,
                    'games': [
                        {
                            'game_id': str,
                            'public_code': str,
                            'game_title': str
                        }
                    ]
                }
            ]

        Raises:
            RepositoryError: If the query operation fails
        """
        pass

    @abstractmethod
    def get_unclaimed_players_in_game(self, game_id: GameId) -> List[Dict]:
        """
        Get all unclaimed players in a specific game.

        Useful for showing users which player identities they can claim.

        Args:
            game_id: The game's ID

        Returns:
            List of dictionaries with unclaimed player details:
            [
                {
                    'player_id': str,
                    'player_name': str,
                    'session_count': int
                }
            ]

        Raises:
            RepositoryError: If the query operation fails
        """
        pass


class RepositoryError(Exception):
    """
    Base exception for repository operations.

    This allows the domain layer to handle persistence errors
    without coupling to specific database technologies.
    """

    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.original_error = original_error
