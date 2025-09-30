"""
Domain services for ledger business logic.

These services contain business rules and operations that don't naturally
belong to a single entity or value object.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional

from domain.poker.exceptions import RepositoryError
from .entities import LedgerEntry, SessionLedger
from .value_objects import LedgerEntryId
from .repositories import LedgerRepository


class LedgerManagementService:
    """
    Domain service for managing ledger operations.

    This service encapsulates the complex business logic around ledger entry
    management, session cleanup, and data consistency operations.
    """

    def __init__(self, ledger_repository: LedgerRepository):
        """
        Initialize the service with required dependencies.

        Args:
            ledger_repository: Repository for ledger persistence operations
        """
        self.ledger_repository = ledger_repository

    def get_game_ledger(self, public_code: str) -> List[LedgerEntry]:
        """
        Get all ledger entries for a game.

        Args:
            public_code: The game's public code

        Returns:
            List of LedgerEntry objects ordered by game number (most recent first)
        """
        return self.ledger_repository.get_all_entries_for_game(public_code)

    def get_ledger_entry(self, session_id: str, player_id: str) -> Optional[LedgerEntry]:
        """
        Get a specific ledger entry.

        Args:
            session_id: The session identifier
            player_id: The player identifier

        Returns:
            LedgerEntry if found, None otherwise
        """
        entry_id = LedgerEntryId(session_id=session_id, player_id=player_id)
        return self.ledger_repository.get_entry_by_id(entry_id)

    def update_ledger_entry(
        self,
        session_id: str,
        player_id: str,
        updates: Dict[str, Any]
    ) -> LedgerEntry:
        """
        Update a ledger entry with new data.

        Args:
            session_id: The session identifier
            player_id: The player identifier
            updates: Dictionary of field updates

        Returns:
            Updated LedgerEntry

        Raises:
            ValueError: If entry not found or validation fails
            RepositoryError: If update operation fails
        """
        # Get existing entry
        entry = self.get_ledger_entry(session_id, player_id)
        if entry is None:
            raise ValueError(f"Ledger entry not found for session {session_id}, player {player_id}")

        # Apply updates
        updated_entry = self._apply_updates(entry, updates)

        # Validate business rules
        self._validate_ledger_entry(updated_entry)

        # Save updated entry
        return self.ledger_repository.save_entry(updated_entry)

    def delete_ledger_entry(self, session_id: str, player_id: str) -> bool:
        """
        Delete a specific ledger entry.

        Args:
            session_id: The session identifier
            player_id: The player identifier

        Returns:
            True if entry was deleted, False if it didn't exist

        Raises:
            RepositoryError: If delete operation fails
        """
        entry_id = LedgerEntryId(session_id=session_id, player_id=player_id)
        return self.ledger_repository.delete_entry(entry_id)

    def delete_entire_session(self, session_id: str) -> int:
        """
        Delete all entries for a session.

        This is a business operation that removes all player participation
        records for a specific session.

        Args:
            session_id: The session identifier

        Returns:
            Number of entries deleted

        Raises:
            RepositoryError: If delete operation fails
        """
        return self.ledger_repository.delete_session_entries(session_id)

    def get_session_ledger(self, session_id: str) -> Optional[SessionLedger]:
        """
        Get the complete ledger for a specific session.

        Args:
            session_id: The session identifier

        Returns:
            SessionLedger with all entries, None if session not found
        """
        return self.ledger_repository.get_session_ledger(session_id)

    def check_session_orphaned(self, session_id: str) -> bool:
        """
        Check if a session has become orphaned (no players).

        Args:
            session_id: The session identifier

        Returns:
            True if session has no players, False otherwise
        """
        return not self.ledger_repository.session_has_players(session_id)

    def get_player_entries_in_game(self, public_code: str, player_id: str) -> List[LedgerEntry]:
        """
        Get all entries for a specific player in a game.

        Args:
            public_code: The game's public code
            player_id: The player identifier

        Returns:
            List of LedgerEntry objects for the player
        """
        return self.ledger_repository.get_entries_for_player_in_game(public_code, player_id)

    def calculate_game_statistics(self, public_code: str) -> Dict[str, Any]:
        """
        Calculate aggregate statistics for a game.

        Args:
            public_code: The game's public code

        Returns:
            Dictionary with game statistics
        """
        entries = self.get_game_ledger(public_code)

        if not entries:
            return {
                "total_entries": 0,
                "total_sessions": 0,
                "total_players": 0,
                "total_pot_cents": 0,
                "profitable_entries": 0,
                "losing_entries": 0
            }

        # Calculate statistics
        unique_sessions = set(entry.get_session_id() for entry in entries)
        unique_players = set(entry.get_player_id() for entry in entries)
        total_pot = sum(entry.financial_summary.buy_in_sum for entry in entries)
        profitable_count = sum(1 for entry in entries if entry.is_profitable())
        losing_count = sum(1 for entry in entries if entry.financial_summary.is_losing())

        return {
            "total_entries": len(entries),
            "total_sessions": len(unique_sessions),
            "total_players": len(unique_players),
            "total_pot_cents": total_pot,
            "total_pot_dollars": total_pot / 100.0,
            "profitable_entries": profitable_count,
            "losing_entries": losing_count,
            "break_even_entries": len(entries) - profitable_count - losing_count
        }

    def _apply_updates(self, entry: LedgerEntry, updates: Dict[str, Any]) -> LedgerEntry:
        """
        Apply updates to a ledger entry.

        Args:
            entry: The original entry
            updates: Dictionary of updates to apply

        Returns:
            Updated LedgerEntry
        """
        updated_entry = entry

        # Handle financial updates
        financial_updates = {}
        if 'buy_in_sum' in updates:
            financial_updates['buy_in_sum'] = int(updates['buy_in_sum'])
        if 'cash_out_sum' in updates:
            financial_updates['cash_out_sum'] = int(updates['cash_out_sum'])
        if 'in_game' in updates:
            financial_updates['in_game'] = int(updates['in_game'])

        if financial_updates:
            updated_entry = updated_entry.update_financial_data(**financial_updates)

        # Handle names update
        if 'names' in updates:
            if not isinstance(updates['names'], list):
                raise ValueError("Names must be a list")
            updated_entry = updated_entry.update_player_names(updates['names'])

        return updated_entry

    def _validate_ledger_entry(self, entry: LedgerEntry) -> None:
        """
        Validate business rules for a ledger entry.

        Args:
            entry: The ledger entry to validate

        Raises:
            ValueError: If validation fails
        """
        # Validate financial consistency (already handled by FinancialSummary)
        # Additional business rules can be added here

        # Example: Validate buy-in is not negative
        if entry.financial_summary.buy_in_sum < 0:
            raise ValueError("Buy-in amount cannot be negative")

        # Example: Validate player has session names
        if not entry.player_names.session_names:
            raise ValueError("Player must have at least one session name")