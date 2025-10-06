"""
Identity domain entities.

Domain entities for user identity and poker identity claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .value_objects import UserId
from ..poker.value_objects import PlayerId


@dataclass
class PokerIdentityClaim:
    """
    Domain entity representing a user's claim to a poker player identity.

    This entity links authenticated users to poker player records, ensuring
    that each player can only be claimed by one user.

    Attributes:
        id: Unique identifier for the claim (UUID string, optional before persistence)
        user_id: User who made the claim
        player_id: Player identity being claimed
        claimed_at: When the claim was made
        verification_method: How the identity was verified (e.g., 'email', 'admin', 'token')
    """

    user_id: UserId
    player_id: PlayerId
    claimed_at: datetime
    verification_method: str
    id: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate poker identity claim data."""
        if not isinstance(self.user_id, UserId):
            raise TypeError("user_id must be a UserId instance")
        if not isinstance(self.player_id, PlayerId):
            raise TypeError("player_id must be a PlayerId instance")
        if not isinstance(self.claimed_at, datetime):
            raise TypeError("claimed_at must be a datetime instance")
        if not isinstance(self.verification_method, str):
            raise TypeError("verification_method must be a string")

        # Validate verification_method is not empty
        if not self.verification_method.strip():
            raise ValueError("verification_method cannot be empty")

        # Validate verification_method length (max 50 chars per schema)
        if len(self.verification_method) > 50:
            raise ValueError("verification_method must be 50 characters or less")

    @classmethod
    def create_new(
        cls,
        user_id: UserId,
        player_id: PlayerId,
        verification_method: str = 'manual',
        claimed_at: Optional[datetime] = None
    ) -> PokerIdentityClaim:
        """
        Factory method to create a new PokerIdentityClaim.

        Args:
            user_id: User making the claim
            player_id: Player identity being claimed
            verification_method: Method used to verify the claim (default: 'manual')
            claimed_at: When the claim was made (default: current time)

        Returns:
            New PokerIdentityClaim instance

        Raises:
            ValueError: If validation fails
            TypeError: If types are invalid
        """
        return cls(
            id=None,  # Will be set after database save
            user_id=user_id,
            player_id=player_id,
            claimed_at=claimed_at or datetime.utcnow(),
            verification_method=verification_method
        )

    def is_verified_by_admin(self) -> bool:
        """Check if this claim was verified by an admin."""
        return self.verification_method == 'admin'

    def is_verified_by_email(self) -> bool:
        """Check if this claim was verified by email."""
        return self.verification_method == 'email'

    def is_verified_by_token(self) -> bool:
        """Check if this claim was verified by token."""
        return self.verification_method == 'token'

    def is_manual_claim(self) -> bool:
        """Check if this was a manual claim."""
        return self.verification_method == 'manual'

    def belongs_to_user(self, user_id: UserId) -> bool:
        """Check if this claim belongs to a specific user."""
        return self.user_id == user_id

    def is_for_player(self, player_id: PlayerId) -> bool:
        """Check if this claim is for a specific player."""
        return self.player_id == player_id

    def days_since_claimed(self, current_date: Optional[datetime] = None) -> int:
        """
        Calculate the number of days since this claim was made.

        Args:
            current_date: Reference date (default: current time)

        Returns:
            Number of days since claim
        """
        reference = current_date or datetime.utcnow()
        delta = reference - self.claimed_at
        return delta.days

    def to_dict(self) -> dict:
        """
        Convert to dictionary format for API responses.

        Returns:
            Dictionary representation of the claim
        """
        return {
            'id': self.id,
            'user_id': str(self.user_id),
            'player_id': str(self.player_id),
            'claimed_at': self.claimed_at.isoformat() if self.claimed_at else None,
            'verification_method': self.verification_method
        }
