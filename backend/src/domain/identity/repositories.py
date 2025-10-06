"""
User repository interface for the identity domain.

This module defines the contract for user persistence operations without
specifying the implementation (database, file system, etc.).

Note: For MVP, repository methods return SQLAlchemy User models directly
rather than domain entities. This simplifies implementation while maintaining
clean separation between domain logic and infrastructure.
"""

from abc import ABC, abstractmethod
from typing import Optional


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
