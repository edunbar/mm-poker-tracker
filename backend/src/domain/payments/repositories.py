"""
Repository interfaces for payment data access.

Provides abstraction over data access for payment transactions and balances.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from domain.poker.value_objects import GameId, PlayerId
from .entities import PaymentTransaction, PlayerBalance


class PaymentRepository(ABC):
    """Abstract repository for payment operations."""

    @abstractmethod
    def save_transaction(self, transaction: PaymentTransaction) -> PaymentTransaction:
        """
        Save a payment transaction.

        Args:
            transaction: The PaymentTransaction to save

        Returns:
            The saved PaymentTransaction with updated transaction_id

        Raises:
            RepositoryError: If save operation fails
        """
        pass

    @abstractmethod
    def get_transaction_by_id(self, transaction_id: str) -> Optional[PaymentTransaction]:
        """
        Get a payment transaction by ID.

        Args:
            transaction_id: The transaction identifier

        Returns:
            PaymentTransaction if found, None otherwise
        """
        pass

    @abstractmethod
    def get_transactions_for_game(self, game_id: GameId) -> List[PaymentTransaction]:
        """
        Get all payment transactions for a game.

        Args:
            game_id: The game identifier

        Returns:
            List of PaymentTransaction objects ordered by payment_date desc
        """
        pass

    @abstractmethod
    def get_transactions_for_player(self, player_id: PlayerId, game_id: GameId) -> List[PaymentTransaction]:
        """
        Get all payment transactions involving a specific player in a game.

        Args:
            player_id: The player identifier
            game_id: The game identifier

        Returns:
            List of PaymentTransaction objects where player is payer or recipient
        """
        pass

    @abstractmethod
    def delete_transaction(self, transaction_id: str) -> bool:
        """
        Delete a payment transaction.

        Args:
            transaction_id: The transaction identifier

        Returns:
            True if transaction was deleted, False if it didn't exist

        Raises:
            RepositoryError: If delete operation fails
        """
        pass


class PaymentBalanceRepository(ABC):
    """Abstract repository for payment balance operations."""

    @abstractmethod
    def get_balance(self, player_id: PlayerId, game_id: GameId) -> Optional[PlayerBalance]:
        """
        Get a player's payment balance for a specific game.

        Args:
            player_id: The player identifier
            game_id: The game identifier

        Returns:
            PlayerBalance if found, None otherwise
        """
        pass

    @abstractmethod
    def get_all_balances_for_game(self, game_id: GameId) -> List[PlayerBalance]:
        """
        Get all player balances for a specific game.

        Args:
            game_id: The game identifier

        Returns:
            List of PlayerBalance objects
        """
        pass

    @abstractmethod
    def save_balance(self, balance: PlayerBalance) -> PlayerBalance:
        """
        Save or update a player balance.

        Args:
            balance: The PlayerBalance to save

        Returns:
            The saved PlayerBalance

        Raises:
            RepositoryError: If save operation fails
        """
        pass

    @abstractmethod
    def update_balances_for_players(self, game_id: GameId, player_ids: List[PlayerId]) -> None:
        """
        Recalculate and update payment balances for specific players in a game.

        This method recalculates balances based on current poker winnings and payments.

        Args:
            game_id: The game identifier
            player_ids: List of player identifiers to update

        Raises:
            RepositoryError: If update operation fails
        """
        pass

    @abstractmethod
    def delete_balance(self, player_id: PlayerId, game_id: GameId) -> bool:
        """
        Delete a player's payment balance record.

        Args:
            player_id: The player identifier
            game_id: The game identifier

        Returns:
            True if balance was deleted, False if it didn't exist

        Raises:
            RepositoryError: If delete operation fails
        """
        pass

    @abstractmethod
    def get_balances_with_player_names(self, public_code: str) -> List[dict]:
        """
        Get payment balances with player names for a game.

        This method returns balance data suitable for API responses,
        including calculated fields and player names.

        Args:
            public_code: The game's public code

        Returns:
            List of dictionaries with balance data and player names
        """
        pass