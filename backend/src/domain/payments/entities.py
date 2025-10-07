"""
Payment domain entities.

Domain entities for payment processing with rich business logic and validation.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Optional

from ..poker.value_objects import Money, PlayerId, GameId
from .value_objects import TransactionId, PaymentMethod, PaymentReference, PaymentNotes, BalanceStatus


@dataclass
class PaymentTransaction:
    """
    Domain entity representing a payment between players.

    This is the core aggregate root for payment operations, encapsulating all data
    and business rules for a single payment transaction.
    """

    transaction_id: str  # Keep as string for compatibility, but validate as UUID
    game_id: GameId
    payer_id: PlayerId
    recipient_id: PlayerId
    amount: Money
    payment_date: datetime
    payment_method: Optional[PaymentMethod] = None
    notes: Optional[PaymentNotes] = None
    reference_id: Optional[PaymentReference] = None
    created_by: str = "admin"

    def __post_init__(self) -> None:
        """Validate payment transaction data."""
        if not isinstance(self.game_id, GameId):
            raise TypeError("game_id must be a GameId instance")
        if not isinstance(self.payer_id, PlayerId):
            raise TypeError("payer_id must be a PlayerId instance")
        if not isinstance(self.recipient_id, PlayerId):
            raise TypeError("recipient_id must be a PlayerId instance")
        if not isinstance(self.amount, Money):
            raise TypeError("amount must be a Money instance")
        if not isinstance(self.payment_date, datetime):
            raise TypeError("payment_date must be a datetime instance")

        # Validate optional value objects
        if self.payment_method is not None and not isinstance(self.payment_method, PaymentMethod):
            raise TypeError("payment_method must be a PaymentMethod instance or None")
        if self.notes is not None and not isinstance(self.notes, PaymentNotes):
            raise TypeError("notes must be a PaymentNotes instance or None")
        if self.reference_id is not None and not isinstance(self.reference_id, PaymentReference):
            raise TypeError("reference_id must be a PaymentReference instance or None")

    @classmethod
    def create_new(
        cls,
        game_id: GameId,
        payer_id: PlayerId,
        recipient_id: PlayerId,
        amount: Money,
        payment_date: datetime,
        payment_method: Optional[str] = None,
        notes: Optional[str] = None,
        reference_id: Optional[str] = None,
        created_by: str = "admin"
    ) -> PaymentTransaction:
        """
        Factory method to create a new PaymentTransaction with validation.

        Args:
            game_id: Game identifier
            payer_id: Player making the payment
            recipient_id: Player receiving the payment
            amount: Payment amount
            payment_date: When the payment was made
            payment_method: Optional payment method
            notes: Optional payment notes
            reference_id: Optional external reference
            created_by: Who created this record

        Returns:
            New PaymentTransaction instance

        Raises:
            ValueError: If validation fails
        """
        # Convert string parameters to value objects
        method_vo = PaymentMethod(payment_method) if payment_method else None
        notes_vo = PaymentNotes(notes) if notes else None
        reference_vo = PaymentReference(reference_id) if reference_id else None

        return cls(
            transaction_id="",  # Will be set after database save
            game_id=game_id,
            payer_id=payer_id,
            recipient_id=recipient_id,
            amount=amount,
            payment_date=payment_date,
            payment_method=method_vo,
            notes=notes_vo,
            reference_id=reference_vo,
            created_by=created_by
        )

    def is_valid(self) -> bool:
        """Check if the transaction is valid."""
        return (
            self.amount.is_positive() and
            self.payer_id != self.recipient_id and
            bool(self.game_id) and
            bool(self.payer_id) and
            bool(self.recipient_id)
        )

    def involves_player(self, player_id: PlayerId) -> bool:
        """Check if the transaction involves a specific player."""
        return self.payer_id == player_id or self.recipient_id == player_id

    def is_payment_from(self, player_id: PlayerId) -> bool:
        """Check if this is a payment from a specific player."""
        return self.payer_id == player_id

    def is_payment_to(self, player_id: PlayerId) -> bool:
        """Check if this is a payment to a specific player."""
        return self.recipient_id == player_id

    def get_amount_dollars(self) -> float:
        """Get the payment amount in dollars."""
        return float(self.amount.amount) / 100.0

    def is_electronic_payment(self) -> bool:
        """Check if this is an electronic payment."""
        return self.payment_method is not None and self.payment_method.is_electronic()

    def has_external_reference(self) -> bool:
        """Check if this payment has an external reference."""
        return self.reference_id is not None

    def with_transaction_id(self, transaction_id: str) -> PaymentTransaction:
        """
        Create a new PaymentTransaction with the specified transaction ID.

        Returns a new instance to maintain immutability.
        """
        return replace(self, transaction_id=transaction_id)

    def to_dict(self) -> dict:
        """Convert to dictionary format for API responses."""
        return {
            "transaction_id": self.transaction_id,
            "game_id": str(self.game_id),
            "payer_id": str(self.payer_id),
            "recipient_id": str(self.recipient_id),
            "amount": self.get_amount_dollars(),
            "payment_date": self.payment_date.isoformat(),
            "payment_method": str(self.payment_method) if self.payment_method else None,
            "notes": str(self.notes) if self.notes else None,
            "reference_id": str(self.reference_id) if self.reference_id else None,
            "created_by": self.created_by
        }


@dataclass
class PlayerBalance:
    """
    Domain entity representing a player's payment balance.

    This entity encapsulates all payment-related data for a player in a specific game,
    including poker winnings, payments made/received, and calculated balances.

    CRITICAL: balance_negative_since field enforces payment-grade invariants:
    - Must be set when balance < 0
    - Must be NULL when balance >= 0
    - Must be timezone-aware UTC timestamp
    - Cannot be in the future
    """

    player_id: PlayerId
    game_id: GameId
    poker_net_winnings: Money
    total_paid: Money
    total_received: Money
    last_payment_date: Optional[datetime] = None
    balance_negative_since: Optional[datetime] = None

    def __post_init__(self) -> None:
        """
        Validate player balance data and enforce payment-grade invariants.

        FAIL FAST: Raises ValueError immediately on invalid states.
        """
        if not isinstance(self.player_id, PlayerId):
            raise TypeError("player_id must be a PlayerId instance")
        if not isinstance(self.game_id, GameId):
            raise TypeError("game_id must be a GameId instance")
        if not isinstance(self.poker_net_winnings, Money):
            raise TypeError("poker_net_winnings must be a Money instance")
        if not isinstance(self.total_paid, Money):
            raise TypeError("total_paid must be a Money instance")
        if not isinstance(self.total_received, Money):
            raise TypeError("total_received must be a Money instance")

        # Validate that paid and received are non-negative
        if not self.total_paid.is_non_negative():
            raise ValueError("Total paid cannot be negative")
        if not self.total_received.is_non_negative():
            raise ValueError("Total received cannot be negative")

        # FAIL FAST: Validate balance_negative_since invariants
        balance = self.balance
        if balance < Money.zero() and self.balance_negative_since is None:
            raise ValueError(
                f"INVARIANT VIOLATION: Negative balance ({balance.amount} cents) "
                f"requires balance_negative_since timestamp. Player: {self.player_id}, Game: {self.game_id}"
            )

        if balance >= Money.zero() and self.balance_negative_since is not None:
            raise ValueError(
                f"INVARIANT VIOLATION: Non-negative balance ({balance.amount} cents) "
                f"cannot have balance_negative_since timestamp. Player: {self.player_id}, Game: {self.game_id}"
            )

        # Validate timezone awareness (UTC required)
        if self.balance_negative_since and self.balance_negative_since.tzinfo is None:
            raise ValueError(
                f"INVARIANT VIOLATION: balance_negative_since must be timezone-aware (UTC). "
                f"Player: {self.player_id}, Game: {self.game_id}"
            )

        # Validate not in future
        if self.balance_negative_since:
            from datetime import timezone as tz
            now_utc = datetime.now(tz.utc)
            if self.balance_negative_since > now_utc:
                raise ValueError(
                    f"INVARIANT VIOLATION: balance_negative_since cannot be in the future. "
                    f"Timestamp: {self.balance_negative_since.isoformat()}, Now: {now_utc.isoformat()}"
                )

    @classmethod
    def create_new(
        cls,
        player_id: PlayerId,
        game_id: GameId,
        poker_net_winnings: Money,
        total_paid: Money = None,
        total_received: Money = None,
        last_payment_date: Optional[datetime] = None,
        balance_negative_since: Optional[datetime] = None
    ) -> PlayerBalance:
        """
        Factory method to create a new PlayerBalance.

        Args:
            player_id: Player identifier
            game_id: Game identifier
            poker_net_winnings: Net winnings from poker
            total_paid: Total amount paid out (defaults to zero)
            total_received: Total amount received (defaults to zero)
            last_payment_date: Date of last payment
            balance_negative_since: Timestamp when balance became negative (if applicable)

        Returns:
            New PlayerBalance instance

        Raises:
            ValueError: If invariants are violated (via __post_init__)
        """
        return cls(
            player_id=player_id,
            game_id=game_id,
            poker_net_winnings=poker_net_winnings,
            total_paid=total_paid or Money.zero(),
            total_received=total_received or Money.zero(),
            last_payment_date=last_payment_date,
            balance_negative_since=balance_negative_since
        )

    @property
    def balance(self) -> Money:
        """
        Calculate payment balance.

        Balance = poker_net_winnings + total_paid - total_received
        Negative: player owes money
        Positive: player is owed money
        Zero: player is settled
        """
        return self.poker_net_winnings + self.total_paid - self.total_received

    @property
    def realized_earnings(self) -> Money:
        """
        Calculate actual cash flow.

        Realized earnings = total_received - total_paid
        """
        return self.total_received - self.total_paid

    @property
    def net_position(self) -> Money:
        """
        Calculate net position for settlement calculations.

        Net position = (poker_winnings + paid_out) - received
        Positive = player is owed money
        Negative = player owes money
        """
        return (self.poker_net_winnings + self.total_paid) - self.total_received

    def get_balance_status(self) -> BalanceStatus:
        """Get the current balance status."""
        balance = self.balance
        if balance.is_zero():
            return BalanceStatus('settled')
        elif balance.is_positive():
            return BalanceStatus('owed_money')
        else:
            return BalanceStatus('owes_money')

    def is_settled(self) -> bool:
        """Check if the player's balance is settled (zero)."""
        return self.balance.is_zero()

    def owes_money(self) -> bool:
        """Check if the player owes money."""
        return self.balance < Money.zero()

    def is_owed_money(self) -> bool:
        """Check if the player is owed money."""
        return self.balance > Money.zero()

    def amount_owed(self) -> Money:
        """Get the amount owed by this player (positive if they owe, zero if they don't)."""
        balance = self.balance
        return Money(abs(balance.amount)) if balance < Money.zero() else Money.zero()

    def amount_due(self) -> Money:
        """Get the amount due to this player (positive if owed, zero if not)."""
        balance = self.balance
        return balance if balance > Money.zero() else Money.zero()

    def days_since_last_payment(self, current_date: datetime) -> Optional[int]:
        """Calculate days since last payment."""
        if self.last_payment_date:
            delta = current_date - self.last_payment_date
            return delta.days
        return None

    def days_balance_negative(self, current_date: datetime) -> Optional[int]:
        """
        Calculate days balance has been continuously negative.

        This is the primary metric for payment overdue alerts.

        Args:
            current_date: Current datetime (must be timezone-aware UTC)

        Returns:
            Number of days balance has been negative, or None if currently non-negative

        Raises:
            ValueError: If balance is negative but balance_negative_since is NULL
                       (database integrity violation - FAIL FAST)

        CRITICAL: This method enforces invariants and fails loudly on violations.
        """
        if self.balance >= Money.zero():
            return None

        if self.balance_negative_since is None:
            raise ValueError(
                f"CRITICAL DATABASE INTEGRITY VIOLATION: Player {self.player_id} "
                f"in game {self.game_id} has negative balance ({self.balance.amount} cents) "
                f"but balance_negative_since is NULL. This should be impossible due to constraints."
            )

        delta = current_date - self.balance_negative_since
        return delta.days

    def has_payment_activity(self) -> bool:
        """Check if the player has any payment activity."""
        return not (self.total_paid.is_zero() and self.total_received.is_zero())

    def record_payment_made(self, amount: Money, payment_date: datetime) -> PlayerBalance:
        """
        Create a new PlayerBalance with recorded outgoing payment.

        Returns a new instance to maintain immutability.
        """
        new_total_paid = self.total_paid + amount
        return replace(
            self,
            total_paid=new_total_paid,
            last_payment_date=payment_date
        )

    def record_payment_received(self, amount: Money, payment_date: datetime) -> PlayerBalance:
        """
        Create a new PlayerBalance with recorded incoming payment.

        Returns a new instance to maintain immutability.
        """
        new_total_received = self.total_received + amount
        return replace(
            self,
            total_received=new_total_received,
            last_payment_date=payment_date
        )

    def to_dict(self) -> dict:
        """Convert to dictionary format for API responses."""
        from datetime import timezone
        now_utc = datetime.now(timezone.utc)

        return {
            "player_id": str(self.player_id),
            "game_id": str(self.game_id),
            "poker_net_winnings": self.poker_net_winnings.amount / 100.0,
            "total_paid": self.total_paid.amount / 100.0,
            "total_received": self.total_received.amount / 100.0,
            "balance": self.balance.amount / 100.0,
            "realized_earnings": self.realized_earnings.amount / 100.0,
            "balance_status": str(self.get_balance_status()),
            "last_payment_date": self.last_payment_date.isoformat() if self.last_payment_date else None,
            "balance_negative_since": self.balance_negative_since.isoformat() if self.balance_negative_since else None,
            "days_since_last_payment": self.days_since_last_payment(now_utc) if self.last_payment_date else None,
            "days_balance_negative": self.days_balance_negative(now_utc)
        }


@dataclass
class SettlementSuggestion:
    """Domain entity representing a suggested payment for debt optimization."""

    payer_id: PlayerId
    payer_name: str
    recipient_id: PlayerId
    recipient_name: str
    amount: Money

    def is_significant(self, threshold: Money = None) -> bool:
        """Check if the suggested payment is significant enough to matter."""
        if threshold is None:
            threshold = Money("0.01")  # 1 cent default
        return self.amount >= threshold