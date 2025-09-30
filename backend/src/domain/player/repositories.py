"""
Repository interfaces for player domain.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from .entities import PlayerIdentity, MergeOperation
from .value_objects import PlayerId, ExternalId
from domain.poker.value_objects import GameId


class PlayerRepository(ABC):
    """Abstract repository for player persistence."""

    @abstractmethod
    def get_by_id(self, player_id: PlayerId) -> Optional[PlayerIdentity]:
        """
        Retrieve a player by ID.

        Args:
            player_id: The player identifier

        Returns:
            PlayerIdentity if found, None otherwise
        """
        pass

    @abstractmethod
    def get_players_in_game(
        self,
        game_id: GameId,
        exclude_player_id: Optional[PlayerId] = None
    ) -> List[PlayerIdentity]:
        """
        Get all players in a game.

        Args:
            game_id: The game identifier
            exclude_player_id: Optional player to exclude from results

        Returns:
            List of PlayerIdentity objects
        """
        pass

    @abstractmethod
    def external_id_exists(
        self,
        external_id: ExternalId,
        exclude_player_id: Optional[PlayerId] = None
    ) -> bool:
        """
        Check if an external ID is already in use.

        Args:
            external_id: The external ID to check
            exclude_player_id: Optional player to exclude from check

        Returns:
            True if external_id exists (and not on excluded player)
        """
        pass

    @abstractmethod
    def save(self, player: PlayerIdentity) -> PlayerIdentity:
        """
        Save or update a player.

        Args:
            player: The player to save

        Returns:
            The saved player identity

        Raises:
            RepositoryError: If save fails
        """
        pass

    @abstractmethod
    def delete(self, player_id: PlayerId) -> bool:
        """
        Delete a player.

        Args:
            player_id: The player to delete

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryError: If delete fails
        """
        pass

    @abstractmethod
    def execute_merge(
        self,
        operation: MergeOperation,
        target_player: PlayerIdentity,
        source_player_ids: List[PlayerId]
    ) -> PlayerIdentity:
        """
        Execute a player merge operation at the persistence layer.

        This handles the database-specific operations like:
        - Moving session summaries
        - Updating game_player links
        - Deleting source players
        - Creating audit logs

        Args:
            operation: The merge operation details
            target_player: The updated target player
            source_player_ids: IDs of source players to delete

        Returns:
            The final merged player identity

        Raises:
            RepositoryError: If merge fails
        """
        pass