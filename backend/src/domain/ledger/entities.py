"""
Domain entities for the ledger domain.

These represent the core business objects for session player summaries and ledger operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import List, Dict, Optional
from datetime import datetime

from domain.poker.value_objects import GameId, PlayerId
from .value_objects import LedgerEntryId, SessionReference, PlayerNames, FinancialSummary


@dataclass
class LedgerEntry:
    """
    Domain entity representing a player's participation in a specific session.

    This is the core aggregate root for ledger operations, encapsulating all data
    about a player's financial activity in a single session.
    """

    id: LedgerEntryId
    game_id: GameId
    session_reference: SessionReference
    player_names: PlayerNames
    financial_summary: FinancialSummary
    session_started_at: Optional[datetime] = None
    session_ended_at: Optional[datetime] = None
    has_csv_data: bool = False

    def __post_init__(self) -> None:
        """Validate ledger entry data."""
        if not isinstance(self.id, LedgerEntryId):
            raise TypeError("id must be a LedgerEntryId instance")
        if not isinstance(self.game_id, GameId):
            raise TypeError("game_id must be a GameId instance")
        if not isinstance(self.session_reference, SessionReference):
            raise TypeError("session_reference must be a SessionReference instance")
        if not isinstance(self.player_names, PlayerNames):
            raise TypeError("player_names must be a PlayerNames instance")
        if not isinstance(self.financial_summary, FinancialSummary):
            raise TypeError("financial_summary must be a FinancialSummary instance")

        # Validate ID consistency
        if self.id.session_id != self.session_reference.session_id:
            raise ValueError("LedgerEntryId session_id must match SessionReference session_id")

        # Validate timestamps
        if (self.session_started_at and self.session_ended_at and
            self.session_started_at > self.session_ended_at):
            raise ValueError("Session start time cannot be after end time")

    @classmethod
    def create_new(
        cls,
        session_id: str,
        player_id: str,
        game_id: GameId,
        external_id: str,
        game_number: int,
        display_name: str,
        session_names: List[str],
        buy_in_sum: int,
        cash_out_sum: int,
        in_game: int,
        session_started_at: Optional[datetime] = None,
        session_ended_at: Optional[datetime] = None,
        has_csv_data: bool = False
    ) -> LedgerEntry:
        """
        Factory method to create a new LedgerEntry with all required components.

        Args:
            session_id: Unique session identifier
            player_id: Unique player identifier
            game_id: Game identifier
            external_id: External session identifier
            game_number: Sequential game number
            display_name: Player's verified name
            session_names: Names used during session
            buy_in_sum: Total buy-in amount (cents)
            cash_out_sum: Total cash-out amount (cents)
            in_game: Amount still in play (cents)
            session_started_at: When session started
            session_ended_at: When session ended
            has_csv_data: Whether CSV data is available

        Returns:
            New LedgerEntry instance
        """
        entry_id = LedgerEntryId(session_id=session_id, player_id=player_id)
        session_ref = SessionReference(
            session_id=session_id,
            external_id=external_id,
            game_number=game_number
        )
        player_names = PlayerNames(
            display_name=display_name,
            session_names=session_names
        )
        financial_summary = FinancialSummary.create(
            buy_in_sum=buy_in_sum,
            cash_out_sum=cash_out_sum,
            in_game=in_game
        )

        return cls(
            id=entry_id,
            game_id=game_id,
            session_reference=session_ref,
            player_names=player_names,
            financial_summary=financial_summary,
            session_started_at=session_started_at,
            session_ended_at=session_ended_at,
            has_csv_data=has_csv_data
        )

    def get_session_id(self) -> str:
        """Get the session ID."""
        return self.id.session_id

    def get_player_id(self) -> str:
        """Get the player ID."""
        return self.id.player_id

    def is_profitable(self) -> bool:
        """Check if this session was profitable for the player."""
        return self.financial_summary.is_profitable()

    def is_session_ended(self) -> bool:
        """Check if the session has ended."""
        return self.session_ended_at is not None

    def get_net_dollars(self) -> float:
        """Get the net result in dollars."""
        return self.financial_summary.net / 100.0

    def update_financial_data(
        self,
        buy_in_sum: Optional[int] = None,
        cash_out_sum: Optional[int] = None,
        in_game: Optional[int] = None
    ) -> LedgerEntry:
        """
        Create a new LedgerEntry with updated financial data.

        Returns a new instance to maintain immutability.
        """
        new_financial = self.financial_summary.with_updated_amounts(
            buy_in_sum=buy_in_sum if buy_in_sum is not None else self.financial_summary.buy_in_sum,
            cash_out_sum=cash_out_sum if cash_out_sum is not None else self.financial_summary.cash_out_sum,
            in_game=in_game if in_game is not None else self.financial_summary.in_game
        )

        return replace(self, financial_summary=new_financial)

    def update_player_names(self, session_names: List[str]) -> LedgerEntry:
        """
        Create a new LedgerEntry with updated session names.

        Returns a new instance to maintain immutability.
        """
        new_player_names = PlayerNames(
            display_name=self.player_names.display_name,
            session_names=session_names
        )

        return replace(self, player_names=new_player_names)

    def to_dict(self) -> Dict:
        """Convert to dictionary format for API responses."""
        return {
            "session_id": self.get_session_id(),
            "player_id": self.get_player_id(),
            "player_name": self.player_names.display_name,
            "session_external_id": self.session_reference.external_id,
            "session_started_at": self.session_started_at.isoformat() if self.session_started_at else None,
            "session_ended_at": self.session_ended_at.isoformat() if self.session_ended_at else None,
            "buy_in_sum": self.financial_summary.buy_in_sum,
            "cash_out_sum": self.financial_summary.cash_out_sum,
            "in_game": self.financial_summary.in_game,
            "net": self.financial_summary.net,
            "names": self.player_names.session_names,
            "game_number": self.session_reference.game_number,
            "has_csv": self.has_csv_data
        }

    def __str__(self) -> str:
        return f"LedgerEntry({self.player_names.display_name} in Session {self.session_reference.game_number})"


@dataclass
class SessionLedger:
    """
    Aggregate root representing all ledger entries for a specific session.

    This entity manages the collection of player summaries within a single session
    and provides operations for session-level manipulations.
    """

    session_reference: SessionReference
    game_id: GameId
    entries: List[LedgerEntry] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate session ledger data."""
        if not isinstance(self.session_reference, SessionReference):
            raise TypeError("session_reference must be a SessionReference instance")
        if not isinstance(self.game_id, GameId):
            raise TypeError("game_id must be a GameId instance")
        if not isinstance(self.entries, list):
            raise TypeError("entries must be a list")

        # Validate all entries belong to this session
        for entry in self.entries:
            if not isinstance(entry, LedgerEntry):
                raise TypeError("All entries must be LedgerEntry instances")
            if entry.session_reference.session_id != self.session_reference.session_id:
                raise ValueError(f"Entry {entry.id} does not belong to session {self.session_reference.session_id}")

    def add_entry(self, entry: LedgerEntry) -> SessionLedger:
        """
        Add a ledger entry to this session.

        Returns a new instance to maintain immutability.
        """
        if entry.session_reference.session_id != self.session_reference.session_id:
            raise ValueError("Entry must belong to this session")

        # Check for duplicates
        for existing in self.entries:
            if existing.id == entry.id:
                raise ValueError(f"Entry {entry.id} already exists in session")

        new_entries = self.entries + [entry]
        return replace(self, entries=new_entries)

    def remove_entry(self, entry_id: LedgerEntryId) -> SessionLedger:
        """
        Remove a ledger entry from this session.

        Returns a new instance to maintain immutability.
        """
        new_entries = [entry for entry in self.entries if entry.id != entry_id]
        if len(new_entries) == len(self.entries):
            raise ValueError(f"Entry {entry_id} not found in session")

        return replace(self, entries=new_entries)

    def get_entry(self, player_id: str) -> Optional[LedgerEntry]:
        """Get an entry by player ID."""
        for entry in self.entries:
            if entry.get_player_id() == player_id:
                return entry
        return None

    def get_player_count(self) -> int:
        """Get the number of players in this session."""
        return len(self.entries)

    def is_empty(self) -> bool:
        """Check if this session has no players."""
        return len(self.entries) == 0

    def calculate_total_pot(self) -> int:
        """Calculate the total pot size (all buy-ins) in cents."""
        return sum(entry.financial_summary.buy_in_sum for entry in self.entries)

    def get_profitable_players(self) -> List[LedgerEntry]:
        """Get all players who were profitable in this session."""
        return [entry for entry in self.entries if entry.is_profitable()]

    def get_losing_players(self) -> List[LedgerEntry]:
        """Get all players who lost money in this session."""
        return [entry for entry in self.entries if entry.financial_summary.is_losing()]

    def __str__(self) -> str:
        return f"SessionLedger(Session {self.session_reference.game_number}, {self.get_player_count()} players)"