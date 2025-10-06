"""
SQLAlchemy implementation of the UserRepository.

This module provides concrete implementation of the repository interface,
working directly with SQLAlchemy User models for MVP simplicity.
"""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from domain.identity.repositories import UserRepository, RepositoryError
from db.models import User


class SQLAlchemyUserRepository(UserRepository):
    """
    SQLAlchemy implementation of UserRepository.

    This repository works directly with SQLAlchemy User models from db.models,
    providing a bridge between domain services and database persistence.

    Attributes:
        db_session: SQLAlchemy database session for executing queries
    """

    def __init__(self, db_session: Session) -> None:
        """
        Initialize the repository with a database session.

        Args:
            db_session: SQLAlchemy database session

        Note:
            The session lifecycle is managed by the caller (typically the web layer).
            This repository does not commit or rollback transactions.
        """
        self.db_session = db_session

    def find_by_email(self, email: str) -> Optional[User]:
        """
        Find a user by email address.

        Args:
            email: The user's email (should be normalized/lowercased)

        Returns:
            User model if found, None otherwise

        Raises:
            RepositoryError: If the database query fails
        """
        try:
            user = self.db_session.query(User).filter(
                User.email == email.lower()
            ).first()
            return user
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"Failed to find user by email: {str(e)}",
                original_error=e
            )

    def find_by_id(self, user_id: str) -> Optional[User]:
        """
        Find a user by ID.

        Args:
            user_id: The user's UUID as a string

        Returns:
            User model if found, None otherwise

        Raises:
            RepositoryError: If the database query fails
        """
        try:
            user = self.db_session.query(User).filter(
                User.id == user_id
            ).first()
            return user
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"Failed to find user by ID: {str(e)}",
                original_error=e
            )

    def create(
        self,
        email: str,
        password_hash: str,
        display_name: str,
        email_verified: bool = False
    ) -> User:
        """
        Create a new user.

        Args:
            email: User's email (normalized/lowercased)
            password_hash: Hashed password
            display_name: User's display name
            email_verified: Whether email is verified

        Returns:
            Created User model

        Raises:
            IntegrityError: If email already exists (unique constraint violation)
            RepositoryError: If the create operation fails
        """
        try:
            user = User(
                email=email.lower(),
                password_hash=password_hash,
                display_name=display_name,
                email_verified=email_verified
            )

            self.db_session.add(user)
            self.db_session.commit()
            self.db_session.refresh(user)

            return user

        except IntegrityError as e:
            self.db_session.rollback()
            # Re-raise IntegrityError for duplicate email handling
            raise

        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise RepositoryError(
                f"Failed to create user: {str(e)}",
                original_error=e
            )

    def update(self, user: User) -> User:
        """
        Update an existing user.

        Args:
            user: User model with updated values

        Returns:
            Updated User model

        Raises:
            RepositoryError: If the update operation fails
        """
        try:
            self.db_session.commit()
            self.db_session.refresh(user)
            return user

        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise RepositoryError(
                f"Failed to update user: {str(e)}",
                original_error=e
            )
