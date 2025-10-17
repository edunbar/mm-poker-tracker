"""
Permission service for live game authorization.

This module provides permission checking logic for live game operations,
determining whether users are authorized to perform administrative actions.
"""

from typing import Callable

from domain.identity.value_objects import UserId
from domain.live_game.value_objects import LiveGameId
from domain.live_game.repositories import LiveGameRepository
from domain.live_game.exceptions import UnauthorizedApprovalError


class LiveGamePermissionService:
    """
    Domain service for checking live game permissions.

    This service determines whether users are authorized to perform
    administrative actions like approving transactions or closing games.

    Authorization Rules:
    - Live game creator can approve transactions
    - Users with admin session for parent game can approve transactions
    - Authorization is checked via external admin session check function

    Attributes:
        live_game_repo: Repository for live game persistence
    """

    def __init__(self, live_game_repo: LiveGameRepository):
        """
        Initialize the permission service.

        Args:
            live_game_repo: Repository for live game operations
        """
        self.live_game_repo = live_game_repo

    def can_approve_transactions(
        self,
        user_id: UserId,
        live_game_id: LiveGameId,
        admin_session_check_fn: Callable[[UserId, str], bool]
    ) -> bool:
        """
        Check if user can approve transactions for a live game.

        A user can approve transactions if:
        1. They created the live game, OR
        2. They have an admin session for the parent game

        Args:
            user_id: User to check authorization for
            live_game_id: Live game identifier
            admin_session_check_fn: Function to check admin session access
                                   Signature: (user_id: UserId, game_id: str) -> bool
                                   Returns True if user has admin access to game

        Returns:
            True if user is authorized, False otherwise

        Example:
            >>> def check_admin_session(user_id: UserId, game_id: str) -> bool:
            ...     # Check if user has admin session for game
            ...     return user_has_admin_access(user_id, game_id)
            ...
            >>> can_approve = service.can_approve_transactions(
            ...     user_id=UserId('user-uuid'),
            ...     live_game_id=LiveGameId('live-game-uuid'),
            ...     admin_session_check_fn=check_admin_session
            ... )
        """
        live_game = self.live_game_repo.get_by_id(live_game_id)
        if not live_game:
            return False

        # Check 1: Is user the creator?
        if live_game.created_by_user_id == user_id:
            return True

        # Check 2: Does user have admin session for parent game?
        if admin_session_check_fn(user_id, str(live_game.game_id)):
            return True

        return False

    def require_approval_permission(
        self,
        user_id: UserId,
        live_game_id: LiveGameId,
        admin_session_check_fn: Callable[[UserId, str], bool]
    ) -> None:
        """
        Raise exception if user cannot approve transactions.

        This is a convenience method for authorization checks in API routes.

        Args:
            user_id: User to check authorization for
            live_game_id: Live game identifier
            admin_session_check_fn: Function to check admin session access

        Raises:
            UnauthorizedApprovalError: If user is not authorized

        Example:
            >>> # In API route
            >>> service.require_approval_permission(
            ...     user_id=current_user_id,
            ...     live_game_id=live_game_id,
            ...     admin_session_check_fn=check_admin_session
            ... )
            >>> # If no exception raised, user is authorized
        """
        if not self.can_approve_transactions(user_id, live_game_id, admin_session_check_fn):
            raise UnauthorizedApprovalError()
