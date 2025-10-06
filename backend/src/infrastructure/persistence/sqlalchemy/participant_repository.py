"""
SQLAlchemy implementation of ParticipantRepository.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from domain.live_game.repositories import ParticipantRepository
from domain.live_game.entities import LiveGameParticipant
from domain.live_game.value_objects import LiveGameId, ParticipantId
from domain.identity.value_objects import UserId
from domain.poker.value_objects import PlayerId
from domain.poker.exceptions import RepositoryError
from db.models import LiveGameParticipant as LiveGameParticipantModel, Player as PlayerModel

logger = logging.getLogger(__name__)


class SQLAlchemyParticipantRepository(ParticipantRepository):
    """SQLAlchemy implementation of participant repository."""

    def __init__(self, db_session: Session):
        self._db_session = db_session

    def get_by_id(self, participant_id: ParticipantId) -> Optional[LiveGameParticipant]:
        """Retrieve a participant by ID."""
        try:
            model = self._db_session.query(LiveGameParticipantModel).filter(
                LiveGameParticipantModel.id == str(participant_id)
            ).first()

            return self._to_entity(model) if model else None

        except SQLAlchemyError as e:
            raise RepositoryError("get_by_id", str(e))

    def get_by_user_and_live_game(
        self,
        user_id: UserId,
        live_game_id: LiveGameId
    ) -> Optional[LiveGameParticipant]:
        """Get a participant by user and live game."""
        try:
            model = self._db_session.query(LiveGameParticipantModel).filter(
                LiveGameParticipantModel.user_id == str(user_id),
                LiveGameParticipantModel.live_game_id == str(live_game_id)
            ).first()

            return self._to_entity(model) if model else None

        except SQLAlchemyError as e:
            raise RepositoryError("get_by_user_and_live_game", str(e))

    def get_by_live_game(self, live_game_id: LiveGameId) -> List[LiveGameParticipant]:
        """
        Get all participants in a live game with enriched player data.

        Uses LEFT JOIN with Player table to fetch claimed player information
        (external_id and display_name) for participants who have claimed a player identity.
        """
        try:
            # Query with LEFT JOIN to Player table
            results = self._db_session.query(
                LiveGameParticipantModel,
                PlayerModel.external_id,
                PlayerModel.display_name
            ).outerjoin(
                PlayerModel,
                LiveGameParticipantModel.player_id == PlayerModel.id
            ).filter(
                LiveGameParticipantModel.live_game_id == str(live_game_id)
            ).order_by(LiveGameParticipantModel.joined_at).all()

            return [
                self._to_entity_with_player(participant_model, player_external_id, player_name)
                for participant_model, player_external_id, player_name in results
            ]

        except SQLAlchemyError as e:
            raise RepositoryError("get_by_live_game", str(e))

    def create(self, participant: LiveGameParticipant) -> LiveGameParticipant:
        """Add a participant to a live game."""
        try:
            model = LiveGameParticipantModel(
                live_game_id=str(participant.live_game_id),
                user_id=str(participant.user_id),
                display_name=participant.display_name,
                player_id=str(participant.player_id) if participant.player_id else None,
                joined_at=participant.joined_at
            )

            self._db_session.add(model)
            self._db_session.flush()

            return self._to_entity(model)

        except SQLAlchemyError as e:
            self._db_session.rollback()
            raise RepositoryError("create", str(e))

    def _to_entity(self, model: LiveGameParticipantModel) -> LiveGameParticipant:
        """Convert SQLAlchemy model to domain entity."""
        return LiveGameParticipant(
            id=ParticipantId(str(model.id)),
            live_game_id=LiveGameId(str(model.live_game_id)),
            user_id=UserId(str(model.user_id)),
            display_name=model.display_name,
            player_id=PlayerId(str(model.player_id)) if model.player_id else None,
            joined_at=model.joined_at
        )

    def _to_entity_with_player(
        self,
        model: LiveGameParticipantModel,
        player_external_id: Optional[str],
        player_name: Optional[str]
    ) -> LiveGameParticipant:
        """
        Convert SQLAlchemy model to domain entity with enriched player data.

        Args:
            model: LiveGameParticipant SQLAlchemy model
            player_external_id: External ID from joined Player table (None if no claim)
            player_name: Display name from joined Player table (None if no claim)

        Returns:
            LiveGameParticipant entity with claimed_player_* fields populated
        """
        return LiveGameParticipant(
            id=ParticipantId(str(model.id)),
            live_game_id=LiveGameId(str(model.live_game_id)),
            user_id=UserId(str(model.user_id)),
            display_name=model.display_name,
            player_id=PlayerId(str(model.player_id)) if model.player_id else None,
            joined_at=model.joined_at,
            claimed_player_external_id=player_external_id,
            claimed_player_name=player_name
        )
