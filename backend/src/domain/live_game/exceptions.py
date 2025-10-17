"""
Domain-specific exceptions for the live game domain.

These exceptions represent business rule violations and domain-specific error
conditions for real-time live poker game tracking.
"""

from typing import Optional
from decimal import Decimal

from domain.poker.exceptions import PokerDomainError


class LiveGameError(PokerDomainError):
    """Base exception for all live game domain errors."""
    pass


class LiveGameNotFoundError(LiveGameError):
    """Raised when a live game cannot be found."""

    def __init__(self, identifier: str) -> None:
        super().__init__(
            f"Live game not found: {identifier}",
            error_code="LIVE_GAME_NOT_FOUND",
            identifier=identifier
        )


class LiveGameAlreadyClosedError(LiveGameError):
    """Raised when attempting to modify a closed live game."""

    def __init__(self) -> None:
        super().__init__(
            "Cannot modify a closed live game",
            error_code="LIVE_GAME_ALREADY_CLOSED"
        )


class ActiveLiveGameExistsError(LiveGameError):
    """Raised when attempting to create a live game when one already exists."""

    def __init__(self, existing_join_code: str) -> None:
        self.existing_join_code = existing_join_code
        super().__init__(
            f"Active live game already exists with code: {existing_join_code}",
            error_code="ACTIVE_LIVE_GAME_EXISTS",
            existing_join_code=existing_join_code
        )


class InvalidJoinCodeError(LiveGameError):
    """Raised when an invalid or expired join code is used."""

    def __init__(self, join_code: str) -> None:
        super().__init__(
            f"Invalid or expired join code: {join_code}",
            error_code="INVALID_JOIN_CODE",
            join_code=join_code
        )


class ParticipantAlreadyJoinedError(LiveGameError):
    """Raised when a user attempts to join a live game they've already joined."""

    def __init__(self) -> None:
        super().__init__(
            "You have already joined this live game",
            error_code="PARTICIPANT_ALREADY_JOINED"
        )


class ParticipantNotFoundError(LiveGameError):
    """Raised when a participant cannot be found in a live game."""

    def __init__(self) -> None:
        super().__init__(
            "Participant not found in this live game",
            error_code="PARTICIPANT_NOT_FOUND"
        )


class InvalidBuyInAmountError(LiveGameError):
    """Raised when a buy-in amount is invalid."""

    def __init__(
        self,
        amount: Decimal,
        min_buy_in: Decimal,
        max_buy_in: Optional[Decimal]
    ) -> None:
        if max_buy_in:
            message = f"Buy-in amount ${amount} must be between ${min_buy_in} and ${max_buy_in}"
        else:
            message = f"Buy-in amount ${amount} must be at least ${min_buy_in}"

        super().__init__(
            message,
            error_code="INVALID_BUY_IN_AMOUNT",
            amount=float(amount),
            min_buy_in=float(min_buy_in),
            max_buy_in=float(max_buy_in) if max_buy_in else None
        )


class InvalidCashOutAmountError(LiveGameError):
    """Raised when a cash-out amount exceeds chips on table."""

    def __init__(self, amount: Decimal, chips_on_table: Decimal) -> None:
        super().__init__(
            f"Cannot cash out ${amount}. You only have ${chips_on_table} in chips",
            error_code="INVALID_CASH_OUT_AMOUNT",
            amount=float(amount),
            chips_on_table=float(chips_on_table)
        )


class TransactionNotFoundError(LiveGameError):
    """Raised when a transaction cannot be found."""

    def __init__(self) -> None:
        super().__init__(
            "Transaction not found",
            error_code="TRANSACTION_NOT_FOUND"
        )


class TransactionNotPendingError(LiveGameError):
    """Raised when attempting to modify a non-pending transaction."""

    def __init__(self) -> None:
        super().__init__(
            "Transaction is not pending",
            error_code="TRANSACTION_NOT_PENDING"
        )


class UnauthorizedApprovalError(LiveGameError):
    """Raised when a user is not authorized to approve transactions."""

    def __init__(self) -> None:
        super().__init__(
            "You are not authorized to approve transactions for this live game",
            error_code="UNAUTHORIZED_APPROVAL"
        )


class GameNotBalancedError(LiveGameError):
    """Raised when attempting to close a game that isn't balanced."""

    def __init__(self, total_buy_ins: Decimal, total_cash_outs: Decimal) -> None:
        difference = total_buy_ins - total_cash_outs
        self.total_buy_ins = total_buy_ins
        self.total_cash_outs = total_cash_outs
        self.difference = difference

        super().__init__(
            f"Game is not balanced. Total buy-ins: ${total_buy_ins}, "
            f"Total cash-outs: ${total_cash_outs}, Difference: ${difference}",
            error_code="GAME_NOT_BALANCED",
            total_buy_ins=float(total_buy_ins),
            total_cash_outs=float(total_cash_outs),
            difference=float(difference)
        )


class PlayersStillActiveError(LiveGameError):
    """Raised when attempting to close a game with players still having chips."""

    def __init__(self, active_count: int) -> None:
        self.active_count = active_count

        super().__init__(
            f"Cannot close game. {active_count} player(s) still have chips on the table",
            error_code="PLAYERS_STILL_ACTIVE",
            active_count=active_count
        )
