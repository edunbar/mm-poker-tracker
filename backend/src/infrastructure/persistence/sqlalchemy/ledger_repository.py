"""
SQLAlchemy implementation of the LedgerRepository.

This module provides concrete implementation of the repository interface,
mapping between domain entities and SQLAlchemy models for ledger operations.
"""

from typing import List, Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_

from domain.ledger.repositories import LedgerRepository
from domain.ledger.entities import LedgerEntry, SessionLedger
from domain.ledger.value_objects import LedgerEntryId, SessionReference, PlayerNames, FinancialSummary
from domain.poker.value_objects import GameId
from domain.poker.exceptions import RepositoryError
from db.models import SessionPlayerSummary, Session as SessionModel, Player, Game


class SQLAlchemyLedgerRepository(LedgerRepository):
    """
    SQLAlchemy implementation of LedgerRepository.

    This repository maps between domain entities (LedgerEntry, SessionLedger) and
    SQLAlchemy models (SessionPlayerSummary, Session, Player, Game).
    """

    def __init__(self, db_session: Session) -> None:
        """
        Initialize the repository with a database session.

        Args:
            db_session: SQLAlchemy database session
        """
        self._db_session = db_session

    def get_all_entries_for_game(self, public_code: str) -> List[LedgerEntry]:
        """
        Get all ledger entries for a specific game.

        Args:
            public_code: The game's public code

        Returns:
            List of all LedgerEntry objects for the game, ordered by game_number desc
        """
        try:
            summaries = self._db_session.query(SessionPlayerSummary).join(
                SessionModel, SessionPlayerSummary.session_id == SessionModel.id
            ).join(
                Game, SessionModel.game_id == Game.id
            ).join(
                Player, SessionPlayerSummary.player_id == Player.id
            ).filter(
                Game.public_code == public_code
            ).options(
                joinedload(SessionPlayerSummary.session).joinedload(SessionModel.game),
                joinedload(SessionPlayerSummary.player)
            ).order_by(SessionModel.game_number.desc()).all()

            return [self._to_domain_entity(summary) for summary in summaries]

        except SQLAlchemyError as e:
            raise RepositoryError("get_all_entries_for_game", str(e))

    def get_entry_by_id(self, entry_id: LedgerEntryId) -> Optional[LedgerEntry]:
        """
        Get a specific ledger entry by its composite ID.

        Args:
            entry_id: The LedgerEntryId (session_id + player_id)

        Returns:
            LedgerEntry if found, None otherwise
        """
        try:
            summary = self._db_session.query(SessionPlayerSummary).join(
                SessionModel, SessionPlayerSummary.session_id == SessionModel.id
            ).join(
                Player, SessionPlayerSummary.player_id == Player.id
            ).filter(
                and_(
                    SessionPlayerSummary.session_id == entry_id.session_id,
                    SessionPlayerSummary.player_id == entry_id.player_id
                )
            ).options(
                joinedload(SessionPlayerSummary.session),
                joinedload(SessionPlayerSummary.player)
            ).first()

            if summary is None:
                return None

            return self._to_domain_entity(summary)

        except SQLAlchemyError as e:
            raise RepositoryError("get_entry_by_id", str(e))

    def get_session_ledger(self, session_id: str) -> Optional[SessionLedger]:
        """
        Get all ledger entries for a specific session.

        Args:
            session_id: The session identifier

        Returns:
            SessionLedger containing all entries for the session, None if session not found
        """
        try:
            # First check if session exists
            session_model = self._db_session.query(SessionModel).filter(
                SessionModel.id == session_id
            ).first()

            if session_model is None:
                return None

            # Get all entries for this session
            summaries = self._db_session.query(SessionPlayerSummary).join(
                Player, SessionPlayerSummary.player_id == Player.id
            ).filter(
                SessionPlayerSummary.session_id == session_id
            ).options(
                joinedload(SessionPlayerSummary.player)
            ).all()

            # Create domain entities
            entries = []
            for summary in summaries:
                summary.session = session_model  # Ensure session is loaded
                entries.append(self._to_domain_entity(summary))

            # Create SessionLedger
            session_ref = SessionReference(
                session_id=str(session_model.id),
                external_id=session_model.external_id,
                game_number=session_model.game_number
            )

            return SessionLedger(
                session_reference=session_ref,
                game_id=GameId(str(session_model.game_id)),
                entries=entries
            )

        except SQLAlchemyError as e:
            raise RepositoryError("get_session_ledger", str(e))

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
        try:
            # Find existing entry
            existing = self._db_session.query(SessionPlayerSummary).filter(
                and_(
                    SessionPlayerSummary.session_id == entry.get_session_id(),
                    SessionPlayerSummary.player_id == entry.get_player_id()
                )
            ).first()

            if existing:
                # Update existing entry
                self._update_db_model(existing, entry)
            else:
                # Create new entry
                new_summary = self._to_db_model(entry)
                self._db_session.add(new_summary)

            self._db_session.flush()
            # Note: Caller is responsible for commit
            return entry

        except SQLAlchemyError as e:
            raise RepositoryError("save_entry", str(e))

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
        try:
            summary = self._db_session.query(SessionPlayerSummary).filter(
                and_(
                    SessionPlayerSummary.session_id == entry_id.session_id,
                    SessionPlayerSummary.player_id == entry_id.player_id
                )
            ).first()

            if summary is None:
                return False

            self._db_session.delete(summary)
            self._db_session.flush()
            # Note: Caller is responsible for commit
            return True

        except SQLAlchemyError as e:
            raise RepositoryError("delete_entry", str(e))

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
        try:
            deleted_count = self._db_session.query(SessionPlayerSummary).filter(
                SessionPlayerSummary.session_id == session_id
            ).delete()

            self._db_session.flush()
            # Note: Caller is responsible for commit
            return deleted_count

        except SQLAlchemyError as e:
            raise RepositoryError("delete_session_entries", str(e))

    def entry_exists(self, entry_id: LedgerEntryId) -> bool:
        """
        Check if a ledger entry exists.

        Args:
            entry_id: The LedgerEntryId to check

        Returns:
            True if entry exists, False otherwise
        """
        try:
            count = self._db_session.query(SessionPlayerSummary).filter(
                and_(
                    SessionPlayerSummary.session_id == entry_id.session_id,
                    SessionPlayerSummary.player_id == entry_id.player_id
                )
            ).count()

            return count > 0

        except SQLAlchemyError as e:
            raise RepositoryError("entry_exists", str(e))

    def get_entries_for_player_in_game(self, public_code: str, player_id: str) -> List[LedgerEntry]:
        """
        Get all entries for a specific player in a specific game.

        Args:
            public_code: The game's public code
            player_id: The player's identifier

        Returns:
            List of LedgerEntry objects for the player in the game
        """
        try:
            summaries = self._db_session.query(SessionPlayerSummary).join(
                SessionModel, SessionPlayerSummary.session_id == SessionModel.id
            ).join(
                Game, SessionModel.game_id == Game.id
            ).join(
                Player, SessionPlayerSummary.player_id == Player.id
            ).filter(
                and_(
                    Game.public_code == public_code,
                    SessionPlayerSummary.player_id == player_id
                )
            ).options(
                joinedload(SessionPlayerSummary.session).joinedload(SessionModel.game),
                joinedload(SessionPlayerSummary.player)
            ).order_by(SessionModel.game_number.desc()).all()

            return [self._to_domain_entity(summary) for summary in summaries]

        except SQLAlchemyError as e:
            raise RepositoryError("get_entries_for_player_in_game", str(e))

    def session_has_players(self, session_id: str) -> bool:
        """
        Check if a session has any players (ledger entries).

        Args:
            session_id: The session identifier

        Returns:
            True if session has players, False otherwise
        """
        try:
            count = self._db_session.query(SessionPlayerSummary).filter(
                SessionPlayerSummary.session_id == session_id
            ).count()

            return count > 0

        except SQLAlchemyError as e:
            raise RepositoryError("session_has_players", str(e))

    def _to_domain_entity(self, db_summary: SessionPlayerSummary) -> LedgerEntry:
        """
        Convert a SQLAlchemy SessionPlayerSummary to a domain LedgerEntry.

        Args:
            db_summary: The SQLAlchemy model

        Returns:
            Domain LedgerEntry entity
        """
        return LedgerEntry.create_new(
            session_id=str(db_summary.session_id),
            player_id=str(db_summary.player_id),
            game_id=GameId(str(db_summary.session.game_id)),
            external_id=db_summary.session.external_id,
            game_number=db_summary.session.game_number,
            display_name=db_summary.player.display_name,
            session_names=db_summary.names or [],
            buy_in_sum=db_summary.buy_in_sum,
            cash_out_sum=db_summary.cash_out_sum,
            in_game=db_summary.in_game,
            session_started_at=db_summary.session.started_at,
            session_ended_at=db_summary.session.ended_at,
            has_csv_data=bool(db_summary.session.ledger_csv_content)
        )

    def _to_db_model(self, entry: LedgerEntry) -> SessionPlayerSummary:
        """
        Convert a domain LedgerEntry to a SQLAlchemy SessionPlayerSummary.

        Args:
            entry: The domain entity

        Returns:
            SQLAlchemy SessionPlayerSummary model
        """
        return SessionPlayerSummary(
            session_id=entry.get_session_id(),
            player_id=entry.get_player_id(),
            buy_in_sum=entry.financial_summary.buy_in_sum,
            cash_out_sum=entry.financial_summary.cash_out_sum,
            in_game=entry.financial_summary.in_game,
            net=entry.financial_summary.net,
            names=entry.player_names.session_names
        )

    def _update_db_model(self, db_summary: SessionPlayerSummary, entry: LedgerEntry) -> None:
        """
        Update a SQLAlchemy model with data from a domain entity.

        Args:
            db_summary: The SQLAlchemy model to update
            entry: The domain entity with new data
        """
        db_summary.buy_in_sum = entry.financial_summary.buy_in_sum
        db_summary.cash_out_sum = entry.financial_summary.cash_out_sum
        db_summary.in_game = entry.financial_summary.in_game
        db_summary.net = entry.financial_summary.net
        db_summary.names = entry.player_names.session_names