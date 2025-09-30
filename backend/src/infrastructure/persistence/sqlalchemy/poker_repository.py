"""
SQLAlchemy implementation of the PokerSessionRepository.

This module provides concrete implementation of the repository interface,
mapping between domain entities and SQLAlchemy models.
"""

from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, NoResultFound

from domain.poker.repositories import (
    PokerSessionRepository,
    RepositoryError,
    SessionNotFoundError as DomainSessionNotFoundError,
    SessionAlreadyExistsError,
    RepositoryConnectionError,
)
from domain.poker.entities.poker_session import PokerSession, SessionState
from domain.poker.value_objects import (
    SessionId,
    PlayerId,
    GameId,
    Money,
    Hand,
    SessionDuration,
)
from db.models import Session as SessionModel, SessionPlayerSummary


class SQLAlchemyPokerSessionRepository(PokerSessionRepository):
    """
    SQLAlchemy implementation of PokerSessionRepository.

    This repository maps between domain entities (PokerSession) and
    SQLAlchemy models (Session, SessionPlayerSummary) in the existing database.

    Note: This implementation assumes that each PokerSession corresponds to
    a SessionPlayerSummary record (player's participation in a session).
    """

    def __init__(self, db_session: Session) -> None:
        """
        Initialize the repository with a database session.

        Args:
            db_session: SQLAlchemy database session
        """
        self._db_session = db_session

    def save(self, session: PokerSession) -> None:
        """
        Save a poker session to the database.

        Maps the domain entity to SQLAlchemy models and persists them.

        Args:
            session: The session to save

        Raises:
            RepositoryError: If the save operation fails
            SessionAlreadyExistsError: If session already exists
        """
        try:
            # Check if session already exists
            existing = self._find_session_model_by_id(session.session_id)

            if existing is not None:
                # Update existing session
                self._update_session_models(existing, session)
            else:
                # Create new session
                self._create_session_models(session)

            self._db_session.flush()  # Note: Caller is responsible for commit

        except IntegrityError as e:
            raise SessionAlreadyExistsError(session.session_id) from e
        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to save session: {e}") from e

    def find_by_id(self, session_id: SessionId) -> Optional[PokerSession]:
        """
        Find a session by its ID.

        Args:
            session_id: The session ID to search for

        Returns:
            The session if found, None otherwise

        Raises:
            RepositoryError: If the query operation fails
        """
        try:
            session_model = self._find_session_model_by_id(session_id)
            if session_model is None:
                return None

            return self._map_to_domain_entity(session_model)

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to find session by ID: {e}") from e

    def find_by_player_id(self, player_id: PlayerId) -> List[PokerSession]:
        """
        Find all sessions for a specific player.

        Args:
            player_id: The player ID to search for

        Returns:
            List of sessions for the player (may be empty)

        Raises:
            RepositoryError: If the query operation fails
        """
        try:
            summaries = (
                self._db_session.query(SessionPlayerSummary)
                .filter(SessionPlayerSummary.player_id == str(player_id))
                .all()
            )

            sessions = []
            for summary in summaries:
                try:
                    session = self._map_to_domain_entity_from_summary(summary)
                    sessions.append(session)
                except Exception:
                    # Skip malformed records, log in production
                    continue

            return sessions

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to find sessions by player ID: {e}") from e

    def find_by_game_id(self, game_id: GameId) -> List[PokerSession]:
        """
        Find all sessions for a specific game.

        Args:
            game_id: The game ID to search for

        Returns:
            List of sessions for the game (may be empty)

        Raises:
            RepositoryError: If the query operation fails
        """
        try:
            # Resolve GameId (public_code) to Game UUID
            from db.models import Game
            game = (
                self._db_session.query(Game)
                .filter(Game.public_code == str(game_id))
                .first()
            )

            if not game:
                return []  # Game not found, return empty list

            sessions_query = (
                self._db_session.query(SessionModel)
                .filter(SessionModel.game_id == game.id)
                .all()
            )

            domain_sessions = []
            for session_model in sessions_query:
                try:
                    # For each session, we need to create domain entities for each player
                    for summary in session_model.summaries:
                        domain_session = self._map_to_domain_entity_from_summary(summary)
                        domain_sessions.append(domain_session)
                except Exception:
                    # Skip malformed records, log in production
                    continue

            return domain_sessions

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to find sessions by game ID: {e}") from e

    def find_active_sessions(self) -> List[PokerSession]:
        """
        Find all currently active sessions.

        Returns:
            List of active sessions (may be empty)

        Raises:
            RepositoryError: If the query operation fails
        """
        try:
            # Active sessions are those without ended_at
            active_session_models = (
                self._db_session.query(SessionModel)
                .filter(SessionModel.ended_at.is_(None))
                .all()
            )

            active_sessions = []
            for session_model in active_session_models:
                try:
                    # Create domain entities for each player in the session
                    for summary in session_model.summaries:
                        domain_session = self._map_to_domain_entity_from_summary(summary)
                        if domain_session.is_active():
                            active_sessions.append(domain_session)
                except Exception:
                    # Skip malformed records, log in production
                    continue

            return active_sessions

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to find active sessions: {e}") from e

    def find_active_sessions_for_player(self, player_id: PlayerId) -> List[PokerSession]:
        """
        Find all active sessions for a specific player.

        Args:
            player_id: The player ID to search for

        Returns:
            List of active sessions for the player (may be empty)

        Raises:
            RepositoryError: If the query operation fails
        """
        try:
            active_summaries = (
                self._db_session.query(SessionPlayerSummary)
                .join(SessionModel)
                .filter(
                    SessionPlayerSummary.player_id == str(player_id),
                    SessionModel.ended_at.is_(None)
                )
                .all()
            )

            active_sessions = []
            for summary in active_summaries:
                try:
                    domain_session = self._map_to_domain_entity_from_summary(summary)
                    if domain_session.is_active():
                        active_sessions.append(domain_session)
                except Exception:
                    # Skip malformed records, log in production
                    continue

            return active_sessions

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to find active sessions for player: {e}") from e

    def find_sessions_by_game_and_player(
        self, game_id: GameId, player_id: PlayerId
    ) -> List[PokerSession]:
        """
        Find all sessions for a specific game and player combination.

        Args:
            game_id: The game ID to search for
            player_id: The player ID to search for

        Returns:
            List of sessions for the game and player (may be empty)

        Raises:
            RepositoryError: If the query operation fails
        """
        try:
            # Resolve GameId (public_code) to Game UUID
            from db.models import Game
            game = (
                self._db_session.query(Game)
                .filter(Game.public_code == str(game_id))
                .first()
            )

            if not game:
                return []  # Game not found, return empty list

            summaries = (
                self._db_session.query(SessionPlayerSummary)
                .join(SessionModel)
                .filter(
                    SessionModel.game_id == game.id,
                    SessionPlayerSummary.player_id == str(player_id)
                )
                .all()
            )

            sessions = []
            for summary in summaries:
                try:
                    session = self._map_to_domain_entity_from_summary(summary)
                    sessions.append(session)
                except Exception:
                    # Skip malformed records, log in production
                    continue

            return sessions

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to find sessions by game and player: {e}") from e

    def delete(self, session_id: SessionId) -> bool:
        """
        Delete a session.

        Args:
            session_id: The session ID to delete

        Returns:
            True if session was deleted, False if not found

        Raises:
            RepositoryError: If the delete operation fails
        """
        try:
            # Find all player summaries for this session
            summaries = (
                self._db_session.query(SessionPlayerSummary)
                .filter(SessionPlayerSummary.session_id == str(session_id))
                .all()
            )

            if not summaries:
                return False

            # Delete the summaries (the session model may remain for other players)
            for summary in summaries:
                self._db_session.delete(summary)

            self._db_session.flush()  # Note: Caller is responsible for commit
            return True

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to delete session: {e}") from e

    def exists(self, session_id: SessionId) -> bool:
        """
        Check if a session exists.

        Args:
            session_id: The session ID to check

        Returns:
            True if session exists, False otherwise

        Raises:
            RepositoryError: If the query operation fails
        """
        try:
            result = (
                self._db_session.query(SessionPlayerSummary)
                .filter(SessionPlayerSummary.session_id == str(session_id))
                .first()
            )
            return result is not None

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to check session existence: {e}") from e

    def count_by_player(self, player_id: PlayerId) -> int:
        """
        Count sessions for a specific player.

        Args:
            player_id: The player ID to count sessions for

        Returns:
            Number of sessions for the player

        Raises:
            RepositoryError: If the query operation fails
        """
        try:
            count = (
                self._db_session.query(SessionPlayerSummary)
                .filter(SessionPlayerSummary.player_id == str(player_id))
                .count()
            )
            return count

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to count sessions by player: {e}") from e

    def count_by_game(self, game_id: GameId) -> int:
        """
        Count sessions for a specific game.

        Args:
            game_id: The game ID to count sessions for

        Returns:
            Number of sessions for the game

        Raises:
            RepositoryError: If the query operation fails
        """
        try:
            # Resolve GameId (public_code) to Game UUID
            from db.models import Game
            game = (
                self._db_session.query(Game)
                .filter(Game.public_code == str(game_id))
                .first()
            )

            if not game:
                return 0  # Game not found, return 0

            count = (
                self._db_session.query(SessionPlayerSummary)
                .join(SessionModel)
                .filter(SessionModel.game_id == game.id)
                .count()
            )
            return count

        except SQLAlchemyError as e:
            raise RepositoryError(f"Failed to count sessions by game: {e}") from e

    # Private mapping methods

    def _find_session_model_by_id(self, session_id: SessionId) -> Optional[SessionModel]:
        """Find a session model by ID."""
        try:
            return (
                self._db_session.query(SessionModel)
                .filter(SessionModel.id == str(session_id))
                .first()
            )
        except NoResultFound:
            return None

    def _map_to_domain_entity(self, session_model: SessionModel) -> PokerSession:
        """
        Map a SessionModel to a domain entity.

        Note: This creates a composite entity representing the session.
        For player-specific data, use _map_to_domain_entity_from_summary.
        """
        # This is a simplified mapping - in practice you might need to choose
        # a specific player or aggregate across all players
        if not session_model.summaries:
            raise ValueError("Session has no player summaries")

        # Use the first player's summary as representative
        first_summary = session_model.summaries[0]
        return self._map_to_domain_entity_from_summary(first_summary)

    def _map_to_domain_entity_from_summary(self, summary: SessionPlayerSummary) -> PokerSession:
        """Map a SessionPlayerSummary to a domain entity."""
        session_model = summary.session

        # Create domain value objects
        session_id = SessionId(str(summary.session_id))
        player_id = PlayerId(str(summary.player_id))

        # Resolve Game UUID to public_code for GameId
        from db.models import Game
        game = (
            self._db_session.query(Game)
            .filter(Game.id == session_model.game_id)
            .first()
        )

        if not game:
            raise ValueError(f"Game not found for UUID: {session_model.game_id}")

        game_id = GameId(game.public_code)

        # Convert financial amounts from cents to dollars
        buy_in_amount = Money(Decimal(summary.buy_in_sum) / 100)

        # Determine if session is ended
        cash_out_amount = None
        ended_at = None
        if session_model.ended_at:
            cash_out_amount = Money(Decimal(summary.cash_out_sum) / 100)
            ended_at = session_model.ended_at

        # Create the domain entity
        poker_session = PokerSession(
            session_id=session_id,
            player_id=player_id,
            game_id=game_id,
            buy_in_amount=buy_in_amount,
            session_type=session_model.session_type,
            session_name=session_model.session_name,
            created_at=session_model.started_at or session_model.created_at,
        )

        # If session is ended, set the ended state
        if cash_out_amount and ended_at:
            # We need to reconstruct the ended state without going through business logic
            poker_session._cash_out_amount = cash_out_amount
            poker_session._ended_at = ended_at
            poker_session._state = SessionState.ENDED

        # Clear any events generated during reconstruction
        poker_session.clear_events()

        # TODO: Load hands from poker_events or hand_summaries if needed
        # This would require additional queries and mapping

        return poker_session

    def _create_session_models(self, domain_session: PokerSession) -> None:
        """Create new SQLAlchemy models from domain entity."""
        # Check if the session model already exists
        session_model = (
            self._db_session.query(SessionModel)
            .filter(SessionModel.id == str(domain_session.session_id))
            .first()
        )

        if not session_model:
            # Resolve GameId (public_code) to Game UUID
            from db.models import Game
            game = (
                self._db_session.query(Game)
                .filter(Game.public_code == str(domain_session.game_id))
                .first()
            )

            if not game:
                raise ValueError(f"Game not found for code: {domain_session.game_id}")

            # Create the session model
            session_model = SessionModel(
                id=str(domain_session.session_id),
                game_id=game.id,  # Use the Game's UUID primary key
                session_type=domain_session.session_type,
                session_name=domain_session.session_name,
                started_at=domain_session.created_at,
                ended_at=domain_session.ended_at,
                created_at=domain_session.created_at,
            )
            self._db_session.add(session_model)

        # Create or update the player summary
        summary = (
            self._db_session.query(SessionPlayerSummary)
            .filter(
                SessionPlayerSummary.session_id == str(domain_session.session_id),
                SessionPlayerSummary.player_id == str(domain_session.player_id)
            )
            .first()
        )

        if not summary:
            buy_in_cents = int(domain_session.buy_in_amount.amount * 100)
            cash_out_cents = int(domain_session.cash_out_amount.amount * 100) if domain_session.cash_out_amount else buy_in_cents
            net_cents = cash_out_cents - buy_in_cents

            summary = SessionPlayerSummary(
                session_id=str(domain_session.session_id),
                player_id=str(domain_session.player_id),
                buy_in_sum=buy_in_cents,
                cash_out_sum=cash_out_cents,
                in_game=0,  # This field needs to be calculated based on your business logic
                net=net_cents,
                names=[],  # This should be populated with player names if available
            )
            self._db_session.add(summary)

    def _update_session_models(self, session_model: SessionModel, domain_session: PokerSession) -> None:
        """Update existing SQLAlchemy models from domain entity."""
        # Update session model
        session_model.ended_at = domain_session.ended_at
        session_model.session_name = domain_session.session_name

        # Update player summary
        summary = (
            self._db_session.query(SessionPlayerSummary)
            .filter(
                SessionPlayerSummary.session_id == str(domain_session.session_id),
                SessionPlayerSummary.player_id == str(domain_session.player_id)
            )
            .first()
        )

        if summary:
            if domain_session.cash_out_amount:
                cash_out_cents = int(domain_session.cash_out_amount.amount * 100)
                summary.cash_out_sum = cash_out_cents
                summary.net = cash_out_cents - summary.buy_in_sum