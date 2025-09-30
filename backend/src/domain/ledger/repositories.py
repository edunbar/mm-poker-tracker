"""
Repository interfaces for ledger data access.

Provides abstraction over data access for ledger entries and session operations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from domain.poker.value_objects import GameId
from .entities import LedgerEntry, SessionLedger
from .value_objects import LedgerEntryId, SessionReference


class LedgerRepository(ABC):
    """Abstract repository for ledger operations."""

    @abstractmethod
    def get_all_entries_for_game(self, public_code: str) -> List[LedgerEntry]:
        """
        Get all ledger entries for a specific game.

        Args:
            public_code: The game's public code

        Returns:
            List of all LedgerEntry objects for the game, ordered by game_number desc
        """
        pass

    @abstractmethod
    def get_entry_by_id(self, entry_id: LedgerEntryId) -> Optional[LedgerEntry]:
        """
        Get a specific ledger entry by its composite ID.

        Args:
            entry_id: The LedgerEntryId (session_id + player_id)

        Returns:
            LedgerEntry if found, None otherwise
        """
        pass

    @abstractmethod
    def get_session_ledger(self, session_id: str) -> Optional[SessionLedger]:
        """
        Get all ledger entries for a specific session.

        Args:
            session_id: The session identifier

        Returns:
            SessionLedger containing all entries for the session, None if session not found
        """
        pass

    @abstractmethod
    def save_entry(self, entry: LedgerEntry) -> LedgerEntry:
        """
        Save or update a ledger entry.

        Args:
            entry: The LedgerEntry to save

        Returns:
            The saved LedgerEntry

        Raises:
            RepositoryError: If save operation fails
        """
        pass

    @abstractmethod
    def delete_entry(self, entry_id: LedgerEntryId) -> bool:
        """
        Delete a specific ledger entry.

        Args:
            entry_id: The LedgerEntryId to delete

        Returns:
            True if entry was deleted, False if it didn't exist

        Raises:
            RepositoryError: If delete operation fails
        """
        pass

    @abstractmethod
    def delete_session_entries(self, session_id: str) -> int:
        """
        Delete all entries for a specific session.

        Args:
            session_id: The session identifier

        Returns:
            Number of entries deleted

        Raises:
            RepositoryError: If delete operation fails
        """
        pass

    @abstractmethod
    def entry_exists(self, entry_id: LedgerEntryId) -> bool:
        """
        Check if a ledger entry exists.

        Args:
            entry_id: The LedgerEntryId to check

        Returns:
            True if entry exists, False otherwise
        """
        pass

    @abstractmethod
    def get_entries_for_player_in_game(self, public_code: str, player_id: str) -> List[LedgerEntry]:
        """
        Get all entries for a specific player in a specific game.

        Args:
            public_code: The game's public code
            player_id: The player's identifier

        Returns:
            List of LedgerEntry objects for the player in the game
        """
        pass

    @abstractmethod
    def session_has_players(self, session_id: str) -> bool:
        """
        Check if a session has any players (ledger entries).

        Args:
            session_id: The session identifier

        Returns:
            True if session has players, False otherwise
        """
        pass