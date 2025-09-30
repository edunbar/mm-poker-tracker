"""
SQLAlchemy implementation of PlayerRepository.
"""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
import logging

from domain.player.repositories import PlayerRepository
from domain.player.entities import PlayerIdentity, PlayerSession, MergeOperation
from domain.player.value_objects import (
    PlayerId, ExternalId, PlayerName, SessionStats
)
from domain.poker.value_objects import GameId
from domain.poker.exceptions import RepositoryError
from db.models import (
    Player as PlayerModel,
    SessionPlayerSummary,
    GamePlayer,
    Game,
    AuditLog
)

logger = logging.getLogger(__name__)


class SQLAlchemyPlayerRepository(PlayerRepository):
    """SQLAlchemy implementation of player repository."""

    def __init__(self, db_session: Session):
        self._db_session = db_session

    def get_by_id(self, player_id: PlayerId) -> Optional[PlayerIdentity]:
        """Retrieve a player by ID with all session data."""
        try:
            player_model = self._db_session.query(PlayerModel).options(
                joinedload(PlayerModel.summaries).joinedload(SessionPlayerSummary.session)
            ).filter(PlayerModel.id == player_id.value).first()

            if not player_model:
                return None

            return self._to_domain_entity(player_model)

        except SQLAlchemyError as e:
            raise RepositoryError("get_by_id", str(e))

    def get_players_in_game(
        self,
        game_id: GameId,
        exclude_player_id: Optional[PlayerId] = None
    ) -> List[PlayerIdentity]:
        """Get all players in a game."""
        try:
            query = self._db_session.query(PlayerModel).join(
                GamePlayer, PlayerModel.id == GamePlayer.player_id
            ).join(
                Game, GamePlayer.game_id == Game.id
            ).filter(
                Game.id == game_id.value
            ).options(
                joinedload(PlayerModel.summaries).joinedload(SessionPlayerSummary.session)
            )

            if exclude_player_id:
                query = query.filter(PlayerModel.id != exclude_player_id.value)

            player_models = query.all()
            return [self._to_domain_entity(p) for p in player_models]

        except SQLAlchemyError as e:
            raise RepositoryError("get_players_in_game", str(e))

    def external_id_exists(
        self,
        external_id: ExternalId,
        exclude_player_id: Optional[PlayerId] = None
    ) -> bool:
        """Check if an external ID is already in use."""
        try:
            query = self._db_session.query(PlayerModel).filter(
                PlayerModel.external_id == external_id.value
            )

            if exclude_player_id:
                query = query.filter(PlayerModel.id != exclude_player_id.value)

            return query.first() is not None

        except SQLAlchemyError as e:
            raise RepositoryError("external_id_exists", str(e))

    def save(self, player: PlayerIdentity) -> PlayerIdentity:
        """Save or update a player."""
        try:
            player_model = self._db_session.query(PlayerModel).filter(
                PlayerModel.id == player.player_id.value
            ).first()

            if not player_model:
                # Create new player
                player_model = PlayerModel(
                    id=player.player_id.value,
                    display_name=player.display_name.value,
                    external_id=player.external_id.value if player.external_id else None
                )
                self._db_session.add(player_model)
            else:
                # Update existing player
                player_model.display_name = player.display_name.value
                if player.external_id:
                    player_model.external_id = player.external_id.value

            self._db_session.flush()
            return player

        except SQLAlchemyError as e:
            self._db_session.rollback()
            raise RepositoryError("save", str(e))

    def delete(self, player_id: PlayerId) -> bool:
        """Delete a player."""
        try:
            player_model = self._db_session.query(PlayerModel).filter(
                PlayerModel.id == player_id.value
            ).first()

            if not player_model:
                return False

            self._db_session.delete(player_model)
            self._db_session.flush()
            return True

        except SQLAlchemyError as e:
            self._db_session.rollback()
            raise RepositoryError("delete", str(e))

    def execute_merge(
        self,
        operation: MergeOperation,
        target_player: PlayerIdentity,
        source_player_ids: List[PlayerId]
    ) -> PlayerIdentity:
        """
        Execute merge at persistence layer.

        Handles:
        1. Moving session summaries from source to target
        2. Updating game_player links
        3. Deleting source players
        4. Creating audit log
        """
        try:
            # Get target model
            target_model = self._db_session.query(PlayerModel).filter(
                PlayerModel.id == target_player.player_id.value
            ).first()

            if not target_model:
                raise ValueError(f"Target player not found: {target_player.player_id}")

            # Get source models
            source_models = self._db_session.query(PlayerModel).filter(
                PlayerModel.id.in_([str(pid) for pid in source_player_ids])
            ).all()

            if len(source_models) != len(source_player_ids):
                raise ValueError("Some source players not found")

            # Capture audit data before merge
            audit_before = self._capture_audit_before(target_model, source_models)

            # Move session summaries and merge duplicates
            for source_model in source_models:
                summaries = self._db_session.query(SessionPlayerSummary).filter(
                    SessionPlayerSummary.player_id == source_model.id
                ).all()

                for summary in summaries:
                    # Check if target already has this session
                    existing_summary = self._db_session.query(SessionPlayerSummary).filter(
                        SessionPlayerSummary.session_id == summary.session_id,
                        SessionPlayerSummary.player_id == target_model.id
                    ).first()

                    if existing_summary:
                        # Merge stats
                        existing_summary.buy_in_sum += summary.buy_in_sum
                        existing_summary.cash_out_sum += summary.cash_out_sum
                        existing_summary.in_game += summary.in_game
                        existing_summary.net += summary.net

                        # Merge names (unique)
                        existing_summary.names = list(set(existing_summary.names + summary.names))

                        # Delete duplicate
                        self._db_session.delete(summary)
                    else:
                        # Move to target
                        summary.player_id = target_model.id

                # Flush session transfers to persist the moved summaries BEFORE deleting player
                self._db_session.flush()

                # Expire source model to clear its collections after flush
                self._db_session.expire(source_model)

                # Update GamePlayer links
                game_links = self._db_session.query(GamePlayer).filter(
                    GamePlayer.player_id == source_model.id
                ).all()

                for link in game_links:
                    existing_link = self._db_session.query(GamePlayer).filter(
                        GamePlayer.game_id == link.game_id,
                        GamePlayer.player_id == target_model.id
                    ).first()

                    if existing_link:
                        # Use earlier join date
                        if link.joined_at < existing_link.joined_at:
                            existing_link.joined_at = link.joined_at
                        self._db_session.delete(link)
                    else:
                        # Move link
                        link.player_id = target_model.id

                # Delete source player
                self._db_session.delete(source_model)

            # Flush deletions
            self._db_session.flush()

            # Update target player
            target_model.display_name = target_player.display_name.value
            if target_player.external_id:
                target_model.external_id = target_player.external_id.value

            # Flush final update
            self._db_session.flush()

            # Capture audit data after merge
            audit_after = self._capture_audit_after(target_model, operation)

            # Create audit log
            audit_entry = AuditLog(
                game_id=None,  # Cross-game operation
                session_id=None,
                actor_kind="admin_code",
                actor_id="system",
                action="PLAYER_MERGE",
                target_table="players",
                target_id=operation.operation_id,
                before=audit_before,
                after=audit_after
            )
            self._db_session.add(audit_entry)

            # Return updated domain entity
            return self.get_by_id(target_player.player_id)

        except SQLAlchemyError as e:
            self._db_session.rollback()
            raise RepositoryError("execute_merge", str(e))

    def _to_domain_entity(self, player_model: PlayerModel) -> PlayerIdentity:
        """Convert database model to domain entity."""
        sessions = []
        for summary in player_model.summaries:
            sessions.append(PlayerSession(
                session_id=str(summary.session_id),
                session_external_id=summary.session.external_id,
                stats=SessionStats(
                    buy_in=summary.buy_in_sum,
                    cash_out=summary.cash_out_sum,
                    net=summary.net,
                    in_game=summary.in_game
                ),
                names_used=summary.names
            ))

        return PlayerIdentity(
            player_id=PlayerId(str(player_model.id)),
            display_name=PlayerName(player_model.display_name),
            external_id=ExternalId(player_model.external_id) if player_model.external_id else None,
            sessions=sessions
        )

    def _capture_audit_before(
        self,
        target_model: PlayerModel,
        source_models: List[PlayerModel]
    ) -> dict:
        """Capture state before merge for audit log."""
        audit_data = {
            'target_player': {
                'id': str(target_model.id),
                'display_name': target_model.display_name,
                'external_id': target_model.external_id,
                'session_count': len(target_model.summaries)
            },
            'source_players': []
        }

        for source in source_models:
            audit_data['source_players'].append({
                'id': str(source.id),
                'display_name': source.display_name,
                'external_id': source.external_id,
                'session_count': len(source.summaries)
            })

        return audit_data

    def _capture_audit_after(
        self,
        target_model: PlayerModel,
        operation: MergeOperation
    ) -> dict:
        """Capture state after merge for audit log."""
        return {
            'operation_id': operation.operation_id,
            'target_player': {
                'id': str(target_model.id),
                'display_name': target_model.display_name,
                'external_id': target_model.external_id,
                'session_count': len(target_model.summaries)
            },
            'merged_player_count': len(operation.source_player_ids),
            'verified_name': str(operation.verified_name)
        }