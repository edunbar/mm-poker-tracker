"""
Poker Identity Claim domain service.

This module provides the core business logic for managing poker identity claims,
including validation and claim lifecycle operations.
"""

from typing import List, Dict
from datetime import datetime

from ..entities import PokerIdentityClaim
from ..repositories import PokerIdentityClaimRepository
from ..value_objects import UserId
from ..exceptions import (
    PlayerNotFoundError,
    PlayerAlreadyClaimedError,
    ClaimNotFoundError,
    UnauthorizedClaimError
)
from domain.player.repositories import PlayerRepository
from domain.poker.value_objects import PlayerId, GameId


class PokerIdentityClaimService:
    """
    Domain service for managing poker identity claims.

    This service encapsulates the business logic for claiming and unclaiming
    poker player identities, coordinating between the claim repository and
    player repository to enforce business rules.

    Business Rules:
    - A player can only be claimed by one user
    - Users can only unclaim their own claims
    - Player must exist before being claimed

    Attributes:
        claim_repository: Repository for poker identity claim persistence
        player_repository: Repository for player persistence
    """

    def __init__(
        self,
        claim_repository: PokerIdentityClaimRepository,
        player_repository: PlayerRepository
    ):
        """
        Initialize the poker identity claim service.

        Args:
            claim_repository: Repository for claim persistence operations
            player_repository: Repository for player persistence operations
        """
        self.claim_repository = claim_repository
        self.player_repository = player_repository

    def get_user_claims(self, user_id: UserId) -> List[Dict]:
        """
        Get all claims for a user with detailed player and game information.

        This method retrieves all poker player identities claimed by a user,
        including information about which games each player participated in.

        Args:
            user_id: The user's ID

        Returns:
            List of dictionaries containing claim details:
            [
                {
                    'claim_id': str,
                    'player_id': str,
                    'player_name': str,
                    'claimed_at': datetime,
                    'verification_method': str,
                    'games': [
                        {
                            'game_id': str,
                            'public_code': str,
                            'game_title': str
                        }
                    ]
                }
            ]

        Example:
            >>> claims = service.get_user_claims(user_id)
            >>> for claim in claims:
            >>>     print(f"{claim['player_name']} plays in {len(claim['games'])} games")
        """
        return self.claim_repository.get_user_claims_with_details(user_id)

    def get_claimable_players_in_game(self, game_id: GameId) -> List[Dict]:
        """
        Get all unclaimed players in a specific game.

        This method retrieves all player identities in a game that haven't
        been claimed yet, useful for showing users which identities they
        can claim.

        Args:
            game_id: The game's ID

        Returns:
            List of dictionaries containing unclaimed player details:
            [
                {
                    'player_id': str,
                    'player_name': str,
                    'session_count': int
                }
            ]

        Example:
            >>> unclaimed = service.get_claimable_players_in_game(game_id)
            >>> print(f"Found {len(unclaimed)} unclaimed players")
        """
        return self.claim_repository.get_unclaimed_players_in_game(game_id)

    def claim_player(
        self,
        user_id: UserId,
        player_id: PlayerId,
        verification_method: str = 'manual'
    ) -> PokerIdentityClaim:
        """
        Claim a poker player identity with full validation.

        This method handles the complete claim process:
        1. Validates that the player exists
        2. Checks if the player is already claimed
        3. Creates the claim if all validations pass

        Args:
            user_id: User making the claim
            player_id: Player identity to claim
            verification_method: How the claim was verified
                                ('manual', 'email', 'admin', 'token')

        Returns:
            Created PokerIdentityClaim entity

        Raises:
            PlayerNotFoundError: If the player doesn't exist
            PlayerAlreadyClaimedError: If the player is already claimed

        Example:
            >>> from domain.identity.value_objects import UserId
            >>> from domain.poker.value_objects import PlayerId
            >>>
            >>> claim = service.claim_player(
            >>>     user_id=UserId('user-uuid'),
            >>>     player_id=PlayerId('player-uuid'),
            >>>     verification_method='email'
            >>> )
            >>> print(f"Claimed player {claim.player_id}")
        """
        # VALIDATION 1: Check player exists
        player = self.player_repository.get_by_id(player_id)
        if not player:
            raise PlayerNotFoundError(str(player_id))

        # VALIDATION 2: Check if already claimed
        existing_claim = self.claim_repository.get_by_player_id(player_id)
        if existing_claim:
            # Check if user already claimed this player
            claimed_by_self = (existing_claim.user_id == user_id)
            raise PlayerAlreadyClaimedError(
                str(player_id),
                claimed_by_self=claimed_by_self
            )

        # CREATE CLAIM
        claim = PokerIdentityClaim.create_new(
            user_id=user_id,
            player_id=player_id,
            verification_method=verification_method
        )

        return self.claim_repository.create(claim)

    def unclaim_player(self, user_id: UserId, claim_id: str) -> bool:
        """
        Unclaim a poker player identity.

        This method handles the complete unclaim process:
        1. Validates that the claim exists
        2. Checks that the user owns the claim
        3. Deletes the claim if all validations pass

        Args:
            user_id: User requesting to unclaim
            claim_id: ID of the claim to remove

        Returns:
            True if claim was successfully deleted

        Raises:
            ClaimNotFoundError: If the claim doesn't exist
            UnauthorizedClaimError: If the user doesn't own the claim

        Example:
            >>> success = service.unclaim_player(
            >>>     user_id=UserId('user-uuid'),
            >>>     claim_id='claim-uuid'
            >>> )
            >>> if success:
            >>>     print("Successfully unclaimed player")
        """
        # VALIDATION 1: Check claim exists
        claim = self.claim_repository.get_by_id(claim_id)
        if not claim:
            raise ClaimNotFoundError(claim_id)

        # VALIDATION 2: Check user owns this claim
        if claim.user_id != user_id:
            raise UnauthorizedClaimError(claim_id, str(user_id))

        # DELETE CLAIM
        return self.claim_repository.delete(claim_id)

    def is_player_claimed(self, player_id: PlayerId) -> bool:
        """
        Check if a player identity has been claimed.

        This is a convenience method for quick checks without needing
        to retrieve the full claim details.

        Args:
            player_id: The player's ID

        Returns:
            True if player is claimed, False otherwise

        Example:
            >>> if service.is_player_claimed(player_id):
            >>>     print("Player already claimed")
        """
        return self.claim_repository.is_player_claimed(player_id)

    def get_claim_for_player(self, player_id: PlayerId) -> PokerIdentityClaim:
        """
        Get the claim for a specific player.

        Args:
            player_id: The player's ID

        Returns:
            PokerIdentityClaim if player is claimed

        Raises:
            ClaimNotFoundError: If player is not claimed

        Example:
            >>> try:
            >>>     claim = service.get_claim_for_player(player_id)
            >>>     print(f"Claimed by user {claim.user_id}")
            >>> except ClaimNotFoundError:
            >>>     print("Player not claimed")
        """
        claim = self.claim_repository.get_by_player_id(player_id)
        if not claim:
            raise ClaimNotFoundError(f"Player {player_id} is not claimed")
        return claim
