"""
Identity domain module.

This module provides domain entities, value objects, repositories, services,
and exceptions for user identity and authentication.
"""

from .value_objects import Email, UserId
from .services import AuthenticationService, PokerIdentityClaimService
from .entities import PokerIdentityClaim
from .repositories import UserRepository, PokerIdentityClaimRepository, RepositoryError
from .exceptions import (
    IdentityDomainError,
    PlayerNotFoundError,
    PlayerAlreadyClaimedError,
    ClaimNotFoundError,
    UnauthorizedClaimError,
    InvalidClaimError
)

__all__ = [
    # Value Objects
    'Email',
    'UserId',
    # Services
    'AuthenticationService',
    'PokerIdentityClaimService',
    # Entities
    'PokerIdentityClaim',
    # Repositories
    'UserRepository',
    'PokerIdentityClaimRepository',
    'RepositoryError',
    # Exceptions
    'IdentityDomainError',
    'PlayerNotFoundError',
    'PlayerAlreadyClaimedError',
    'ClaimNotFoundError',
    'UnauthorizedClaimError',
    'InvalidClaimError'
]
