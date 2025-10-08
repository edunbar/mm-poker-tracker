"""
Service layer for managing player payment methods.

Payment methods are GLOBAL per player (not per-game). A player's Venmo handle
is the same across all games they participate in.

Key Features:
- Players can have multiple payment methods (e.g., 3 Venmo accounts, 2 Zelles)
- Only ONE method can be marked as primary across all their methods
- Basic validation: trim whitespace, auto-add @ to Venmo handles
- Atomic primary-setting: unset all primaries, then set new one
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from db.models import PlayerPaymentMethod, Player, GamePlayer
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class PlayerPaymentMethodService:
    """Service for managing player payment method preferences."""

    def __init__(self, db_session: Session):
        self.db = db_session

    @staticmethod
    def _validate_and_clean_address(payment_method: str, payment_address: str) -> str:
        """
        Validate and clean payment address.

        - Trim whitespace
        - Auto-add @ to Venmo if missing
        - Reject empty addresses

        Args:
            payment_method: Payment method type (Venmo, Zelle, etc.)
            payment_address: Raw address/handle

        Returns:
            Cleaned payment address

        Raises:
            ValueError: If address is empty after trimming
        """
        address = payment_address.strip()

        if not address:
            raise ValueError("Payment address cannot be empty")

        # Auto-add @ to Venmo handles if missing
        if payment_method.lower() == "venmo" and not address.startswith("@"):
            address = f"@{address}"

        return address

    def get_player_payment_methods(self, player_id: str) -> List[Dict[str, Any]]:
        """
        Get all payment methods for a specific player.

        Args:
            player_id: UUID of the player

        Returns:
            List of payment method dictionaries
        """
        methods = self.db.query(PlayerPaymentMethod).filter(
            PlayerPaymentMethod.player_id == player_id
        ).order_by(
            PlayerPaymentMethod.is_primary.desc(),  # Primary first
            PlayerPaymentMethod.created_at.asc()
        ).all()

        return [
            {
                "id": str(method.id),
                "player_id": str(method.player_id),
                "payment_method": method.payment_method,
                "payment_address": method.payment_address,
                "is_primary": method.is_primary,
                "created_at": method.created_at.isoformat(),
                "updated_at": method.updated_at.isoformat()
            }
            for method in methods
        ]

    def get_all_payment_methods_for_game(self, game_id: str) -> List[Dict[str, Any]]:
        """
        Get all payment methods for all players in a game.

        Args:
            game_id: UUID of the game

        Returns:
            List of player payment method data with player names
        """
        # Get all players in this game
        game_players = self.db.query(Player).join(
            GamePlayer, GamePlayer.player_id == Player.id
        ).filter(
            GamePlayer.game_id == game_id
        ).all()

        result = []
        for player in game_players:
            methods = self.db.query(PlayerPaymentMethod).filter(
                PlayerPaymentMethod.player_id == player.id
            ).order_by(
                PlayerPaymentMethod.is_primary.desc(),
                PlayerPaymentMethod.created_at.asc()
            ).all()

            result.append({
                "player_id": str(player.id),
                "player_name": player.display_name,
                "methods": [
                    {
                        "id": str(method.id),
                        "payment_method": method.payment_method,
                        "payment_address": method.payment_address,
                        "is_primary": method.is_primary,
                        "created_at": method.created_at.isoformat(),
                        "updated_at": method.updated_at.isoformat()
                    }
                    for method in methods
                ]
            })

        return result

    def add_payment_method(
        self,
        player_id: str,
        payment_method: str,
        payment_address: str,
        is_primary: bool = False
    ) -> Dict[str, Any]:
        """
        Add a new payment method for a player.

        Args:
            player_id: UUID of the player
            payment_method: Payment method type (Venmo, Zelle, etc.)
            payment_address: Handle/phone/email
            is_primary: Whether to set as primary method

        Returns:
            Created payment method dictionary

        Raises:
            ValueError: If validation fails
            IntegrityError: If setting primary conflicts with existing primary
        """
        # Validate player exists
        player = self.db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise ValueError(f"Player {player_id} not found")

        # Validate and clean address
        cleaned_address = self._validate_and_clean_address(payment_method, payment_address)

        # If setting as primary, unset all other primaries first (atomic operation)
        if is_primary:
            self._unset_all_primaries(player_id)

        # Create new payment method
        new_method = PlayerPaymentMethod(
            player_id=player_id,
            payment_method=payment_method,
            payment_address=cleaned_address,
            is_primary=is_primary
        )

        self.db.add(new_method)
        self.db.flush()  # Get ID before commit

        logger.info(f"Added payment method for player {player_id}: {payment_method} ({cleaned_address})")

        return {
            "id": str(new_method.id),
            "player_id": str(new_method.player_id),
            "payment_method": new_method.payment_method,
            "payment_address": new_method.payment_address,
            "is_primary": new_method.is_primary,
            "created_at": new_method.created_at.isoformat(),
            "updated_at": new_method.updated_at.isoformat()
        }

    def update_payment_method(
        self,
        method_id: str,
        payment_method: Optional[str] = None,
        payment_address: Optional[str] = None,
        is_primary: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Update an existing payment method.

        Args:
            method_id: UUID of the payment method
            payment_method: New payment method type (optional)
            payment_address: New address (optional)
            is_primary: New primary status (optional)

        Returns:
            Updated payment method dictionary

        Raises:
            ValueError: If method not found or validation fails
        """
        method = self.db.query(PlayerPaymentMethod).filter(
            PlayerPaymentMethod.id == method_id
        ).first()

        if not method:
            raise ValueError(f"Payment method {method_id} not found")

        # Update fields if provided
        if payment_method is not None:
            method.payment_method = payment_method

        if payment_address is not None:
            # Use updated payment_method if provided, otherwise existing
            current_method = payment_method if payment_method is not None else method.payment_method
            cleaned_address = self._validate_and_clean_address(current_method, payment_address)
            method.payment_address = cleaned_address

        # Handle primary setting atomically
        if is_primary is not None and is_primary and not method.is_primary:
            # Setting this as primary - unset all other primaries first
            self._unset_all_primaries(str(method.player_id))
            method.is_primary = True
        elif is_primary is not None and not is_primary:
            method.is_primary = False

        method.updated_at = datetime.now(timezone.utc)
        self.db.flush()

        logger.info(f"Updated payment method {method_id}")

        return {
            "id": str(method.id),
            "player_id": str(method.player_id),
            "payment_method": method.payment_method,
            "payment_address": method.payment_address,
            "is_primary": method.is_primary,
            "created_at": method.created_at.isoformat(),
            "updated_at": method.updated_at.isoformat()
        }

    def set_primary(self, method_id: str) -> Dict[str, Any]:
        """
        Set a payment method as primary (atomic operation).

        This will unset all other primaries for this player and set this one.

        Args:
            method_id: UUID of the payment method

        Returns:
            Updated payment method dictionary

        Raises:
            ValueError: If method not found
        """
        method = self.db.query(PlayerPaymentMethod).filter(
            PlayerPaymentMethod.id == method_id
        ).first()

        if not method:
            raise ValueError(f"Payment method {method_id} not found")

        # Atomic operation: unset all primaries, then set this one
        self._unset_all_primaries(str(method.player_id))
        method.is_primary = True
        method.updated_at = datetime.now(timezone.utc)
        self.db.flush()

        logger.info(f"Set payment method {method_id} as primary for player {method.player_id}")

        return {
            "id": str(method.id),
            "player_id": str(method.player_id),
            "payment_method": method.payment_method,
            "payment_address": method.payment_address,
            "is_primary": method.is_primary,
            "created_at": method.created_at.isoformat(),
            "updated_at": method.updated_at.isoformat()
        }

    def delete_payment_method(self, method_id: str) -> None:
        """
        Delete a payment method.

        Args:
            method_id: UUID of the payment method

        Raises:
            ValueError: If method not found
        """
        method = self.db.query(PlayerPaymentMethod).filter(
            PlayerPaymentMethod.id == method_id
        ).first()

        if not method:
            raise ValueError(f"Payment method {method_id} not found")

        logger.info(f"Deleting payment method {method_id} for player {method.player_id}")

        self.db.delete(method)
        self.db.flush()

    def _unset_all_primaries(self, player_id: str) -> None:
        """
        Unset all primary flags for a player's payment methods.

        This is called before setting a new primary to ensure atomicity.

        Args:
            player_id: UUID of the player
        """
        self.db.query(PlayerPaymentMethod).filter(
            PlayerPaymentMethod.player_id == player_id,
            PlayerPaymentMethod.is_primary == True
        ).update(
            {"is_primary": False, "updated_at": datetime.now(timezone.utc)},
            synchronize_session='fetch'
        )
