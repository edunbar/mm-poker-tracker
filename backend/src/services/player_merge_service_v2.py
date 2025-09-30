"""
Player Merge Service V2 - Domain-based implementation.

Uses domain entities, value objects, and repositories for player merging operations.
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from db.database import SessionLocal
from domain.player.entities import PlayerIdentity, MergeCandidate, MergeOperation
from domain.player.value_objects import PlayerId, PlayerName, ExternalId
from domain.player.services import PlayerMatchingService, PlayerMergeService
from domain.player.repositories import PlayerRepository
from domain.poker.value_objects import GameId
from infrastructure.persistence.sqlalchemy.player_repository import SQLAlchemyPlayerRepository

logger = logging.getLogger(__name__)


class PlayerMergeServiceV2:
    """
    Domain-based player merge service.

    Provides clean API for finding duplicate players and merging them,
    with all business logic encapsulated in the domain layer.
    """

    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize service with database session.

        Args:
            db_session: Optional SQLAlchemy session. If not provided,
                       service will create and manage its own session.
        """
        if db_session is None:
            self._db_session = SessionLocal()
            self._should_close_session = True
        else:
            self._db_session = db_session
            self._should_close_session = False

        self._player_repo: PlayerRepository = SQLAlchemyPlayerRepository(self._db_session)
        self._matching_service = PlayerMatchingService()
        self._merge_service = PlayerMergeService()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes session if we created it."""
        if self._should_close_session and self._db_session:
            self._db_session.close()

    def find_potential_duplicates(
        self,
        game_id: str,
        verified_name: str,
        exclude_player_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Find potential duplicate players for a given verified name.

        Uses fuzzy matching on display names and session names.

        Args:
            game_id: Game ID or public code to search within
            verified_name: The name to match against
            exclude_player_id: Optional player ID to exclude from results

        Returns:
            Dictionary with match results:
            {
                'verified_name': str,
                'potential_matches': List[dict],
                'match_count': int
            }
        """
        try:
            # Convert to domain value objects
            domain_game_id = GameId(game_id)
            domain_verified_name = PlayerName(verified_name)
            domain_exclude_id = PlayerId(exclude_player_id) if exclude_player_id else None

            # Get all players in game
            candidates = self._player_repo.get_players_in_game(
                domain_game_id,
                exclude_player_id=domain_exclude_id
            )

            # Find matches using domain service
            matches: List[MergeCandidate] = self._matching_service.find_matches(
                domain_verified_name,
                candidates
            )

            # Convert to API response format
            return {
                'verified_name': verified_name,
                'potential_matches': [m.to_dict() for m in matches],
                'match_count': len(matches)
            }

        except Exception as e:
            logger.error(f"Error finding potential duplicates: {e}")
            raise

    def merge_players(
        self,
        target_player_id: str,
        source_player_ids: List[str],
        verified_name: str,
        external_id: Optional[str] = None,
        admin_code: Optional[str] = None,
        game_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Merge multiple players into a single target player.

        All session summaries from source players are moved to target player.
        Source players are deleted after merge.

        Args:
            target_player_id: ID of player to merge into
            source_player_ids: List of player IDs to merge and delete
            verified_name: Verified display name for merged player
            external_id: Optional external ID (e.g., Venmo handle)
            admin_code: Admin code for audit logging
            game_id: Optional game ID for audit logging

        Returns:
            Dictionary with merge results

        Raises:
            ValueError: If merge validation fails
        """
        try:
            # Convert to domain value objects
            domain_target_id = PlayerId(target_player_id)
            domain_source_ids = [PlayerId(sid) for sid in source_player_ids]
            domain_verified_name = PlayerName(verified_name)
            domain_external_id = ExternalId(external_id) if external_id else None

            # Get players from repository
            target_player = self._player_repo.get_by_id(domain_target_id)
            if not target_player:
                raise ValueError(f"Target player not found: {target_player_id}")

            source_players = []
            for source_id in domain_source_ids:
                player = self._player_repo.get_by_id(source_id)
                if not player:
                    raise ValueError(f"Source player not found: {source_id}")
                source_players.append(player)

            # Validate external_id if provided
            if domain_external_id:
                if self._player_repo.external_id_exists(
                    domain_external_id,
                    exclude_player_id=domain_target_id
                ):
                    # Check if it's from one of the source players
                    has_match = any(
                        p.external_id == domain_external_id
                        for p in source_players
                    )
                    if not has_match:
                        raise ValueError(
                            f"External ID '{external_id}' is already assigned to another player"
                        )

            # Prepare merge operation using domain service
            operation = self._merge_service.prepare_merge(
                target_player,
                source_players,
                domain_verified_name,
                domain_external_id
            )

            # Execute merge in domain layer
            merge_result = self._merge_service.execute_merge(
                operation,
                target_player,
                source_players
            )

            # Persist merge to database
            final_player = self._player_repo.execute_merge(
                operation,
                merge_result.merged_player,
                domain_source_ids
            )

            # Commit if we own the session
            if self._should_close_session:
                self._db_session.commit()

            # Return result
            result_dict = merge_result.to_dict()
            result_dict['final_player_id'] = str(final_player.player_id)

            logger.info(
                f"Successfully merged {len(source_player_ids)} players into {target_player_id}"
            )

            return result_dict

        except Exception as e:
            if self._should_close_session:
                self._db_session.rollback()
            logger.error(f"Error merging players: {e}")
            raise


# Backward compatibility functions
def find_potential_duplicates(
    public_code: str,
    verified_name: str,
    exclude_player_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Backward compatible function for finding duplicates.

    Creates its own session and service instance.
    """
    with PlayerMergeServiceV2() as service:
        return service.find_potential_duplicates(
            game_id=public_code,
            verified_name=verified_name,
            exclude_player_id=exclude_player_id
        )


def merge_players(
    target_player_id: str,
    source_player_ids: List[str],
    verified_name: str,
    external_id: Optional[str] = None,
    admin_code: Optional[str] = None,
    game_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Backward compatible function for merging players.

    Creates its own session and service instance.
    """
    with PlayerMergeServiceV2() as service:
        return service.merge_players(
            target_player_id=target_player_id,
            source_player_ids=source_player_ids,
            verified_name=verified_name,
            external_id=external_id,
            admin_code=admin_code,
            game_id=game_id
        )