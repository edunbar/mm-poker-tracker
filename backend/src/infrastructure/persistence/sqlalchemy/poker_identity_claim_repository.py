"""
SQLAlchemy implementation of PokerIdentityClaimRepository.

This module provides concrete implementation of the repository interface,
mapping between domain entities and SQLAlchemy models for poker identity claim operations.
"""

from typing import Optional, List, Dict
from datetime import datetime

from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from domain.identity.repositories import PokerIdentityClaimRepository, RepositoryError
from domain.identity.entities import PokerIdentityClaim
from domain.identity.value_objects import UserId
from domain.poker.value_objects import PlayerId, GameId
from db.models import (
    PokerIdentityClaim as ClaimModel,
    Player as PlayerModel,
    GamePlayer,
    Game as GameModel
)


class SQLAlchemyPokerIdentityClaimRepository(PokerIdentityClaimRepository):
    """
    SQLAlchemy implementation of PokerIdentityClaimRepository.

    This repository maps between domain entities (PokerIdentityClaim) and
    SQLAlchemy models (PokerIdentityClaim) in the existing database.
    """

    def __init__(self, db_session: Session) -> None:
        """
        Initialize the repository with a database session.

        Args:
            db_session: SQLAlchemy database session

        Note:
            The session lifecycle is managed by the caller (typically the web layer).
            This repository does not commit transactions in most cases.
        """
        self._db_session = db_session

    def get_by_id(self, claim_id: str) -> Optional[PokerIdentityClaim]:
        """
        Get a claim by its ID.

        Args:
            claim_id: The claim's UUID as a string

        Returns:
            PokerIdentityClaim if found, None otherwise

        Raises:
            RepositoryError: If the query operation fails
        """
        try:
            db_claim = self._db_session.query(ClaimModel).filter(
                ClaimModel.id == claim_id
            ).first()

            if db_claim is None:
                return None

            return self._to_domain_entity(db_claim)

        except SQLAlchemyError as e:
            raise RepositoryError(
                f"Failed to get claim by ID: {str(e)}",
                original_error=e
            )

    def get_by_user_id(self, user_id: UserId) -> List[PokerIdentityClaim]:
        """
        Get all claims for a specific user.

        Args:
            user_id: The user's ID

        Returns:
            List of PokerIdentityClaim entities (may be empty)

        Raises:
            RepositoryError: If the query operation fails
        """
        try:
            db_claims = self._db_session.query(ClaimModel).filter(
                ClaimModel.user_id == user_id.value
            ).all()

            return [self._to_domain_entity(claim) for claim in db_claims]

        except SQLAlchemyError as e:
            raise RepositoryError(
                f"Failed to get claims by user ID: {str(e)}",
                original_error=e
            )

    def get_by_player_id(self, player_id: PlayerId) -> Optional[PokerIdentityClaim]:
        """
        Get the claim for a specific player (if claimed).

        Args:
            player_id: The player's ID

        Returns:
            PokerIdentityClaim if the player is claimed, None otherwise

        Raises:
            RepositoryError: If the query operation fails
        """
        try:
            db_claim = self._db_session.query(ClaimModel).filter(
                ClaimModel.player_id == player_id.value
            ).first()

            if db_claim is None:
                return None

            return self._to_domain_entity(db_claim)

        except SQLAlchemyError as e:
            raise RepositoryError(
                f"Failed to get claim by player ID: {str(e)}",
                original_error=e
            )

    def is_player_claimed(self, player_id: PlayerId) -> bool:
        """
        Check if a player has been claimed by a user.

        Args:
            player_id: The player's ID

        Returns:
            True if claimed, False otherwise

        Raises:
            RepositoryError: If the query operation fails
        """
        try:
            count = self._db_session.query(ClaimModel).filter(
                ClaimModel.player_id == player_id.value
            ).count()

            return count > 0

        except SQLAlchemyError as e:
            raise RepositoryError(
                f"Failed to check if player is claimed: {str(e)}",
                original_error=e
            )

    def create(self, claim: PokerIdentityClaim) -> PokerIdentityClaim:
        """
        Create a new poker identity claim.

        Args:
            claim: The claim to create

        Returns:
            Created PokerIdentityClaim with populated ID

        Raises:
            IntegrityError: If the player is already claimed
            RepositoryError: If the create operation fails
        """
        try:
            # Convert domain entity to SQLAlchemy model
            db_claim = ClaimModel(
                user_id=claim.user_id.value,
                player_id=claim.player_id.value,
                claimed_at=claim.claimed_at,
                verification_method=claim.verification_method
            )

            self._db_session.add(db_claim)
            self._db_session.commit()
            self._db_session.refresh(db_claim)

            # Return domain entity with populated ID
            return self._to_domain_entity(db_claim)

        except IntegrityError as e:
            self._db_session.rollback()
            # Re-raise IntegrityError for duplicate claim handling
            raise

        except SQLAlchemyError as e:
            self._db_session.rollback()
            raise RepositoryError(
                f"Failed to create claim: {str(e)}",
                original_error=e
            )

    def delete(self, claim_id: str) -> bool:
        """
        Delete a claim by its ID.

        Args:
            claim_id: The claim's UUID as a string

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryError: If the delete operation fails
        """
        try:
            db_claim = self._db_session.query(ClaimModel).filter(
                ClaimModel.id == claim_id
            ).first()

            if db_claim is None:
                return False

            self._db_session.delete(db_claim)
            self._db_session.commit()

            return True

        except SQLAlchemyError as e:
            self._db_session.rollback()
            raise RepositoryError(
                f"Failed to delete claim: {str(e)}",
                original_error=e
            )

    def get_user_claims_with_details(self, user_id: UserId) -> List[Dict]:
        """
        Get all claims for a user with joined player and game data.

        Returns detailed information for each claimed player including
        which games they've participated in.

        Args:
            user_id: The user's ID

        Returns:
            List of dictionaries with claim, player, and game details

        Raises:
            RepositoryError: If the query operation fails
        """
        try:
            # Query claims with player data
            claims_with_players = self._db_session.query(
                ClaimModel, PlayerModel
            ).join(
                PlayerModel, ClaimModel.player_id == PlayerModel.id
            ).filter(
                ClaimModel.user_id == user_id.value
            ).all()

            result = []
            for claim, player in claims_with_players:
                # Get all games this player participated in
                games_query = self._db_session.query(GameModel).join(
                    GamePlayer, GameModel.id == GamePlayer.game_id
                ).filter(
                    GamePlayer.player_id == player.id
                ).all()

                games_list = [
                    {
                        'game_id': str(game.id),
                        'public_code': game.public_code,
                        'game_title': game.title
                    }
                    for game in games_query
                ]

                result.append({
                    'claim_id': str(claim.id),
                    'player_id': str(player.id),
                    'player_name': player.display_name,
                    'claimed_at': claim.claimed_at,
                    'verification_method': claim.verification_method,
                    'games': games_list
                })

            return result

        except SQLAlchemyError as e:
            raise RepositoryError(
                f"Failed to get user claims with details: {str(e)}",
                original_error=e
            )

    def get_unclaimed_players_in_game(self, game_id: GameId) -> List[Dict]:
        """
        Get all unclaimed players in a specific game.

        Useful for showing users which player identities they can claim.

        Args:
            game_id: The game's ID

        Returns:
            List of dictionaries with unclaimed player details

        Raises:
            RepositoryError: If the query operation fails
        """
        try:
            # Query players in the game who don't have a claim
            unclaimed_players = self._db_session.query(PlayerModel).join(
                GamePlayer, PlayerModel.id == GamePlayer.player_id
            ).outerjoin(
                ClaimModel, PlayerModel.id == ClaimModel.player_id
            ).filter(
                GamePlayer.game_id == game_id.value,
                ClaimModel.id.is_(None)  # No claim exists
            ).all()

            result = []
            for player in unclaimed_players:
                # Count sessions for this player
                session_count = len(player.summaries)

                result.append({
                    'player_id': str(player.id),
                    'player_name': player.display_name,
                    'session_count': session_count
                })

            return result

        except SQLAlchemyError as e:
            raise RepositoryError(
                f"Failed to get unclaimed players in game: {str(e)}",
                original_error=e
            )

    def _to_domain_entity(self, db_claim: ClaimModel) -> PokerIdentityClaim:
        """
        Convert a SQLAlchemy model to a domain PokerIdentityClaim entity.

        Args:
            db_claim: The SQLAlchemy model

        Returns:
            Domain PokerIdentityClaim entity
        """
        return PokerIdentityClaim(
            id=str(db_claim.id),
            user_id=UserId(str(db_claim.user_id)),
            player_id=PlayerId(str(db_claim.player_id)),
            claimed_at=db_claim.claimed_at,
            verification_method=db_claim.verification_method
        )
