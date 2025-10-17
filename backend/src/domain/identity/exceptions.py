"""
Domain-specific exceptions for the identity domain.

These exceptions represent business rule violations and domain-specific error
conditions for user identity and poker identity claims.
"""

from domain.poker.exceptions import PokerDomainError


class IdentityDomainError(PokerDomainError):
    """Base exception for all identity domain errors."""
    pass


class PlayerNotFoundError(IdentityDomainError):
    """Raised when a player cannot be found."""

    def __init__(self, player_id: str) -> None:
        super().__init__(
            f"Player with ID '{player_id}' was not found",
            error_code="PLAYER_NOT_FOUND",
            player_id=player_id
        )


class PlayerAlreadyClaimedError(IdentityDomainError):
    """Raised when attempting to claim a player that's already claimed."""

    def __init__(self, player_id: str, claimed_by_self: bool = False) -> None:
        if claimed_by_self:
            message = f"You have already claimed player '{player_id}'"
        else:
            message = f"Player '{player_id}' has already been claimed by another user"

        super().__init__(
            message,
            error_code="PLAYER_ALREADY_CLAIMED",
            player_id=player_id,
            claimed_by_self=claimed_by_self
        )


class ClaimNotFoundError(IdentityDomainError):
    """Raised when a claim cannot be found."""

    def __init__(self, claim_id: str) -> None:
        super().__init__(
            f"Claim with ID '{claim_id}' was not found",
            error_code="CLAIM_NOT_FOUND",
            claim_id=claim_id
        )


class UnauthorizedClaimError(IdentityDomainError):
    """Raised when a user attempts to modify a claim they don't own."""

    def __init__(self, claim_id: str, user_id: str) -> None:
        super().__init__(
            f"User '{user_id}' is not authorized to modify claim '{claim_id}'",
            error_code="UNAUTHORIZED_CLAIM",
            claim_id=claim_id,
            user_id=user_id
        )


class InvalidClaimError(IdentityDomainError):
    """Raised when claim validation fails."""

    def __init__(self, reason: str, **context) -> None:
        super().__init__(
            f"Invalid claim: {reason}",
            error_code="INVALID_CLAIM",
            reason=reason,
            **context
        )
