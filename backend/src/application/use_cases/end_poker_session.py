"""
Use case for ending a poker session.

This use case orchestrates the business process of ending a poker session,
including domain logic, persistence, payment processing, and event handling.
"""

from typing import Protocol, List
from dataclasses import dataclass

from ...domain.poker.repositories import PokerSessionRepository, RepositoryError
from ...domain.poker.value_objects import SessionId, Money
from ...domain.poker.events import DomainEvent, LargeWinEvent
from ...domain.poker.exceptions import (
    SessionNotFoundError,
    SessionAlreadyEndedError,
    InvalidCashOutAmountError,
)


class PaymentProcessor(Protocol):
    """Protocol for payment processing services."""

    def process_profitable_session(self, session_id: str, profit_amount: Money) -> bool:
        """
        Process payment for a profitable session.

        Args:
            session_id: ID of the session
            profit_amount: Amount of profit to process

        Returns:
            True if payment was successfully processed
        """
        ...


class DomainEventPublisher(Protocol):
    """Protocol for publishing domain events."""

    def publish_events(self, events: List[DomainEvent]) -> None:
        """
        Publish a list of domain events.

        Args:
            events: List of domain events to publish
        """
        ...


class LargeWinNotificationService(Protocol):
    """Protocol for large win notification services."""

    def notify_large_win(self, player_id: str, session_id: str, profit: Money) -> None:
        """
        Send notification for large win.

        Args:
            player_id: ID of the player
            session_id: ID of the session
            profit: Amount of profit
        """
        ...


@dataclass
class EndPokerSessionCommand:
    """Command for ending a poker session."""

    session_id: str
    cash_out_amount: str  # String to avoid precision issues in JSON/HTTP


@dataclass
class EndPokerSessionResult:
    """Result of ending a poker session."""

    session_id: str
    player_id: str
    profit: str
    hourly_rate: str
    session_duration_minutes: int
    is_profitable: bool
    is_large_win: bool
    payment_processed: bool
    events_published: int


class EndPokerSessionError(Exception):
    """Base exception for end poker session use case errors."""

    def __init__(self, message: str, error_code: str, **context) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context


class EndPokerSessionUseCase:
    """
    Use case for ending a poker session.

    This orchestrates the entire business process of ending a session,
    including domain validation, payment processing, and event publishing.
    """

    def __init__(
        self,
        session_repository: PokerSessionRepository,
        payment_processor: PaymentProcessor | None = None,
        event_publisher: DomainEventPublisher | None = None,
        notification_service: LargeWinNotificationService | None = None,
    ) -> None:
        """
        Initialize the use case.

        Args:
            session_repository: Repository for session persistence
            payment_processor: Optional payment processing service
            event_publisher: Optional domain event publisher
            notification_service: Optional large win notification service
        """
        self._session_repository = session_repository
        self._payment_processor = payment_processor
        self._event_publisher = event_publisher
        self._notification_service = notification_service

    def execute(self, command: EndPokerSessionCommand) -> EndPokerSessionResult:
        """
        Execute the end poker session use case.

        Args:
            command: Command containing session ID and cash out amount

        Returns:
            Result containing session details and processing status

        Raises:
            EndPokerSessionError: If the use case fails
        """
        try:
            # Parse and validate inputs
            session_id = SessionId(command.session_id)
            cash_out_amount = Money(command.cash_out_amount)

        except ValueError as e:
            raise EndPokerSessionError(
                f"Invalid input parameters: {e}",
                "INVALID_INPUT",
                session_id=command.session_id,
                cash_out_amount=command.cash_out_amount,
            ) from e

        try:
            # Find the session
            session = self._session_repository.find_by_id(session_id)
            if session is None:
                raise EndPokerSessionError(
                    f"Session not found: {session_id}",
                    "SESSION_NOT_FOUND",
                    session_id=str(session_id),
                )

            # Check if already ended (business rule validation)
            if session.is_ended():
                raise EndPokerSessionError(
                    f"Session {session_id} is already ended",
                    "SESSION_ALREADY_ENDED",
                    session_id=str(session_id),
                )

            # End the session (domain logic)
            session.end_session(cash_out_amount)

            # Calculate derived values
            profit = session.calculate_profit()
            hourly_rate = session.calculate_hourly_rate()
            duration = session.get_duration()
            is_profitable = session.is_profitable()

            # Persist the changes
            self._session_repository.save(session)

            # Process payments for profitable sessions
            payment_processed = False
            if is_profitable and self._payment_processor:
                try:
                    payment_processed = self._payment_processor.process_profitable_session(
                        str(session_id), profit
                    )
                except Exception as e:
                    # Log the error but don't fail the entire operation
                    # In production, you might want to queue this for retry
                    print(f"Payment processing failed: {e}")

            # Check for large win and send notifications
            is_large_win = False
            events = session.domain_events
            for event in events:
                if isinstance(event, LargeWinEvent):
                    is_large_win = True
                    if self._notification_service:
                        try:
                            self._notification_service.notify_large_win(
                                str(session.player_id), str(session_id), profit
                            )
                        except Exception as e:
                            # Log the error but don't fail the entire operation
                            print(f"Large win notification failed: {e}")

            # Publish domain events
            events_published = 0
            if self._event_publisher and events:
                try:
                    self._event_publisher.publish_events(events)
                    events_published = len(events)
                except Exception as e:
                    # Log the error but don't fail the entire operation
                    print(f"Event publishing failed: {e}")

            # Clear events after publishing
            session.clear_events()

            return EndPokerSessionResult(
                session_id=str(session_id),
                player_id=str(session.player_id),
                profit=str(profit.amount),
                hourly_rate=str(hourly_rate.amount),
                session_duration_minutes=duration.minutes,
                is_profitable=is_profitable,
                is_large_win=is_large_win,
                payment_processed=payment_processed,
                events_published=events_published,
            )

        except (
            SessionNotFoundError,
            SessionAlreadyEndedError,
            InvalidCashOutAmountError,
        ) as e:
            raise EndPokerSessionError(
                str(e),
                e.error_code if hasattr(e, 'error_code') else "DOMAIN_ERROR",
                session_id=str(session_id),
            ) from e

        except RepositoryError as e:
            raise EndPokerSessionError(
                f"Repository operation failed: {e}",
                "REPOSITORY_ERROR",
                session_id=str(session_id),
            ) from e

        except Exception as e:
            raise EndPokerSessionError(
                f"Unexpected error: {e}",
                "UNEXPECTED_ERROR",
                session_id=str(session_id),
            ) from e


# Concrete implementations for common scenarios

class NoOpPaymentProcessor:
    """No-operation payment processor for testing or when payments are disabled."""

    def process_profitable_session(self, session_id: str, profit_amount: Money) -> bool:
        """Always return True without processing."""
        return True


class LoggingEventPublisher:
    """Event publisher that logs events instead of publishing them."""

    def publish_events(self, events: List[DomainEvent]) -> None:
        """Log events instead of publishing."""
        for event in events:
            print(f"Event: {event.event_type()} - {event.to_dict()}")


class ConsoleNotificationService:
    """Notification service that prints to console."""

    def notify_large_win(self, player_id: str, session_id: str, profit: Money) -> None:
        """Print large win notification to console."""
        print(f"🎉 Large win alert! Player {player_id} won ${profit.amount} in session {session_id}")


# Factory function for easy setup

def create_end_poker_session_use_case(
    session_repository: PokerSessionRepository,
    enable_payments: bool = False,
    enable_events: bool = False,
    enable_notifications: bool = False,
) -> EndPokerSessionUseCase:
    """
    Factory function to create EndPokerSessionUseCase with common configurations.

    Args:
        session_repository: Repository for session persistence
        enable_payments: Whether to enable payment processing
        enable_events: Whether to enable event publishing
        enable_notifications: Whether to enable notifications

    Returns:
        Configured EndPokerSessionUseCase instance
    """
    payment_processor = NoOpPaymentProcessor() if enable_payments else None
    event_publisher = LoggingEventPublisher() if enable_events else None
    notification_service = ConsoleNotificationService() if enable_notifications else None

    return EndPokerSessionUseCase(
        session_repository=session_repository,
        payment_processor=payment_processor,
        event_publisher=event_publisher,
        notification_service=notification_service,
    )