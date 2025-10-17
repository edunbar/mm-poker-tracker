"""
SQLAlchemy implementation of LiveGameRepository.
"""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from domain.live_game.repositories import LiveGameRepository
from domain.live_game.entities import LiveGame
from domain.live_game.value_objects import LiveGameId, JoinCode
from domain.poker.value_objects import GameId
from domain.identity.value_objects import UserId
from domain.poker.exceptions import RepositoryError
from db.models import LiveGame as LiveGameModel

logger = logging.getLogger(__name__)


class SQLAlchemyLiveGameRepository(LiveGameRepository):
    """SQLAlchemy implementation of live game repository."""

    def __init__(self, db_session: Session):
        self._db_session = db_session

    def get_by_id(self, live_game_id: LiveGameId) -> Optional[LiveGame]:
        """Retrieve a live game by its ID."""
        try:
            model = self._db_session.query(LiveGameModel).filter(
                LiveGameModel.id == str(live_game_id)
            ).first()

            return self._to_entity(model) if model else None

        except SQLAlchemyError as e:
            raise RepositoryError("get_by_id", str(e))

    def get_by_join_code(self, join_code: JoinCode) -> Optional[LiveGame]:
        """Retrieve a live game by its join code."""
        try:
            model = self._db_session.query(LiveGameModel).filter(
                LiveGameModel.join_code == join_code.value
            ).first()

            return self._to_entity(model) if model else None

        except SQLAlchemyError as e:
            raise RepositoryError("get_by_join_code", str(e))

    def get_active_by_game_id(self, game_id: GameId) -> Optional[LiveGame]:
        """Get the currently active live game for a parent game."""
        try:
            model = self._db_session.query(LiveGameModel).filter(
                LiveGameModel.game_id == str(game_id),
                LiveGameModel.status == 'active'
            ).first()

            return self._to_entity(model) if model else None

        except SQLAlchemyError as e:
            raise RepositoryError("get_active_by_game_id", str(e))

    def create(self, live_game: LiveGame) -> LiveGame:
        """Create a new live game."""
        try:
            model = LiveGameModel(
                game_id=str(live_game.game_id),
                created_by_user_id=str(live_game.created_by_user_id) if live_game.created_by_user_id else None,
                join_code=live_game.join_code.value,
                status=live_game.status,
                small_blind=live_game.small_blind,
                big_blind=live_game.big_blind,
                min_buy_in=live_game.min_buy_in,
                max_buy_in=live_game.max_buy_in,
                started_at=live_game.started_at,
                closed_at=live_game.closed_at
            )

            self._db_session.add(model)
            self._db_session.flush()

            return self._to_entity(model)

        except SQLAlchemyError as e:
            self._db_session.rollback()
            raise RepositoryError("create", str(e))

    def update(self, live_game: LiveGame) -> LiveGame:
        """Update an existing live game."""
        try:
            model = self._db_session.query(LiveGameModel).filter(
                LiveGameModel.id == str(live_game.id)
            ).first()

            if not model:
                raise RepositoryError("update", f"Live game not found: {live_game.id}")

            # Update fields
            model.status = live_game.status
            model.closed_at = live_game.closed_at
            model.small_blind = live_game.small_blind
            model.big_blind = live_game.big_blind
            model.min_buy_in = live_game.min_buy_in
            model.max_buy_in = live_game.max_buy_in

            self._db_session.flush()

            return self._to_entity(model)

        except SQLAlchemyError as e:
            self._db_session.rollback()
            raise RepositoryError("update", str(e))

    def join_code_exists(self, join_code_str: str) -> bool:
        """Check if a join code already exists."""
        try:
            count = self._db_session.query(LiveGameModel).filter(
                LiveGameModel.join_code == join_code_str
            ).count()

            return count > 0

        except SQLAlchemyError as e:
            raise RepositoryError("join_code_exists", str(e))

    def _to_entity(self, model: LiveGameModel) -> LiveGame:
        """Convert SQLAlchemy model to domain entity."""
        return LiveGame(
            id=LiveGameId(str(model.id)),
            game_id=GameId(str(model.game_id)),
            created_by_user_id=UserId(str(model.created_by_user_id)) if model.created_by_user_id else None,
            join_code=JoinCode(model.join_code),
            status=model.status,
            small_blind=model.small_blind,
            big_blind=model.big_blind,
            min_buy_in=model.min_buy_in,
            max_buy_in=model.max_buy_in,
            started_at=model.started_at,
            closed_at=model.closed_at
        )
