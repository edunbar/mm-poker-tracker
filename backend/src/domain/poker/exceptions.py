"""
Domain-specific exceptions for the poker domain.

These exceptions represent business rule violations and domain-specific error conditions.
They are part of the ubiquitous language and should be meaningful to domain experts.
"""

from typing import Any


class PokerDomainError(Exception):
    """Base exception for all poker domain errors."""

    def __init__(self, message: str, error_code: str | None = None, **kwargs: Any) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = kwargs


class SessionAlreadyEndedError(PokerDomainError):
    """Raised when attempting to modify an already ended session."""

    def __init__(self, session_id: str) -> None:
        super().__init__(
            f"Session {session_id} has already been ended",
            error_code="SESSION_ALREADY_ENDED",
            session_id=session_id
        )


class InvalidCashOutAmountError(PokerDomainError):
    """Raised when attempting to cash out with an invalid amount."""

    def __init__(self, amount: Any, reason: str) -> None:
        super().__init__(
            f"Invalid cash out amount {amount}: {reason}",
            error_code="INVALID_CASH_OUT_AMOUNT",
            amount=amount,
            reason=reason
        )


class SessionExpiredError(PokerDomainError):
    """Raised when a session has exceeded its maximum duration."""

    def __init__(self, session_id: str, max_hours: int = 24) -> None:
        super().__init__(
            f"Session {session_id} has exceeded maximum duration of {max_hours} hours",
            error_code="SESSION_EXPIRED",
            session_id=session_id,
            max_hours=max_hours
        )


class MaximumHandsExceededError(PokerDomainError):
    """Raised when attempting to add more hands than allowed."""

    def __init__(self, current_hands: int, max_hands: int = 1000) -> None:
        super().__init__(
            f"Cannot add hand: {current_hands} hands already played, maximum is {max_hands}",
            error_code="MAXIMUM_HANDS_EXCEEDED",
            current_hands=current_hands,
            max_hands=max_hands
        )


class InvalidSessionStateError(PokerDomainError):
    """Raised when attempting an operation on a session in an invalid state."""

    def __init__(self, session_id: str, current_state: str, required_state: str) -> None:
        super().__init__(
            f"Session {session_id} is in state '{current_state}', but operation requires '{required_state}'",
            error_code="INVALID_SESSION_STATE",
            session_id=session_id,
            current_state=current_state,
            required_state=required_state
        )


class DuplicateHandNumberError(PokerDomainError):
    """Raised when attempting to add a hand with a duplicate hand number."""

    def __init__(self, hand_number: int) -> None:
        super().__init__(
            f"Hand number {hand_number} already exists in this session",
            error_code="DUPLICATE_HAND_NUMBER",
            hand_number=hand_number
        )


class NegativeMoneyAmountError(PokerDomainError):
    """Raised when attempting to use a negative money amount where not allowed."""

    def __init__(self, amount: Any, context: str) -> None:
        super().__init__(
            f"Negative money amount not allowed in {context}: {amount}",
            error_code="NEGATIVE_MONEY_AMOUNT",
            amount=amount,
            context=context
        )


class SessionNotFoundError(PokerDomainError):
    """Raised when a session cannot be found."""

    def __init__(self, session_id: str) -> None:
        super().__init__(
            f"Session with ID {session_id} was not found",
            error_code="SESSION_NOT_FOUND",
            session_id=session_id
        )


# ==========================================================
# Game Domain Exceptions
# ==========================================================

class GameDomainError(PokerDomainError):
    """Base exception for all game domain errors."""
    pass


class GameNotFoundError(GameDomainError):
    """Raised when a game cannot be found."""

    def __init__(self, identifier: str, identifier_type: str = "ID") -> None:
        super().__init__(
            f"Game with {identifier_type} '{identifier}' was not found",
            error_code="GAME_NOT_FOUND",
            identifier=identifier,
            identifier_type=identifier_type
        )


class DuplicatePublicCodeError(GameDomainError):
    """Raised when attempting to create a game with a duplicate public code."""

    def __init__(self, public_code: str) -> None:
        super().__init__(
            f"Game with public code '{public_code}' already exists",
            error_code="DUPLICATE_PUBLIC_CODE",
            public_code=public_code
        )


class DuplicateAdminTokenError(GameDomainError):
    """Raised when attempting to create a game with a duplicate admin token."""

    def __init__(self) -> None:
        super().__init__(
            "A game with this admin token already exists",
            error_code="DUPLICATE_ADMIN_TOKEN"
        )


class RepositoryError(GameDomainError):
    """Raised when a repository operation fails."""

    def __init__(self, operation: str, details: str | None = None) -> None:
        message = f"Repository operation '{operation}' failed"
        if details:
            message += f": {details}"
        super().__init__(
            message,
            error_code="REPOSITORY_ERROR",
            operation=operation,
            details=details
        )


class GameCreationError(GameDomainError):
    """Raised when game creation fails due to business rule violations."""

    def __init__(self, reason: str, attempts: int | None = None) -> None:
        message = f"Game creation failed: {reason}"
        if attempts:
            message += f" (after {attempts} attempts)"
        super().__init__(
            message,
            error_code="GAME_CREATION_FAILED",
            reason=reason,
            attempts=attempts
        )