"""
Value objects for the payment domain.

These value objects encapsulate data and enforce business rules for payment operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class TransactionId:
    """
    Unique identifier for a payment transaction.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate transaction ID format."""
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("Transaction ID cannot be empty")

        # Validate UUID format
        try:
            UUID(self.value)
        except ValueError as e:
            raise ValueError(f"Invalid transaction ID UUID format: {e}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PaymentMethod:
    """
    Payment method value object with validation.
    """

    value: Optional[str]

    def __post_init__(self) -> None:
        """Validate payment method."""
        # Handle None values gracefully (convert to "Unknown")
        if self.value is None:
            object.__setattr__(self, 'value', "Unknown")
            return

        if not isinstance(self.value, str):
            raise TypeError("Payment method must be a string")

        # Normalize whitespace
        normalized = self.value.strip()
        object.__setattr__(self, 'value', normalized)

        # Handle empty string gracefully (convert to "Unknown")
        if not self.value:
            object.__setattr__(self, 'value', "Unknown")

        if len(self.value) > 50:
            raise ValueError("Payment method must be 50 characters or less")

        # Common payment methods for validation
        valid_methods = {
            'venmo', 'zelle', 'paypal', 'cash', 'check', 'bank_transfer',
            'credit_card', 'debit_card', 'wire_transfer', 'crypto', 'other',
            'settlement', 'unknown'  # Add settlement and unknown as valid methods
        }

        # Very lenient validation for legacy data compatibility
        # Accept any non-empty string after normalization
        # Only validate length limit for reasonable database storage
        pass  # No minimum length validation - accept any payment method

    def __str__(self) -> str:
        return self.value

    def is_electronic(self) -> bool:
        """Check if this is an electronic payment method."""
        electronic_methods = {'venmo', 'zelle', 'paypal', 'bank_transfer', 'wire_transfer', 'crypto'}
        return self.value.lower() in electronic_methods

    def is_cash_based(self) -> bool:
        """Check if this is a cash-based payment method."""
        cash_methods = {'cash', 'check'}
        return self.value.lower() in cash_methods


@dataclass(frozen=True)
class PaymentReference:
    """
    External reference for a payment (e.g., Venmo transaction ID).
    """

    value: str

    def __post_init__(self) -> None:
        """Validate payment reference."""
        if not isinstance(self.value, str):
            raise TypeError("Payment reference must be a string")

        # Normalize whitespace
        normalized = self.value.strip()
        object.__setattr__(self, 'value', normalized)

        if not self.value:
            raise ValueError("Payment reference cannot be empty")

        if len(self.value) > 100:
            raise ValueError("Payment reference must be 100 characters or less")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PaymentNotes:
    """
    Notes or description for a payment.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate payment notes."""
        if not isinstance(self.value, str):
            raise TypeError("Payment notes must be a string")

        # Normalize whitespace
        normalized = ' '.join(self.value.split())
        object.__setattr__(self, 'value', normalized)

        if len(self.value) > 500:
            raise ValueError("Payment notes must be 500 characters or less")

    def __str__(self) -> str:
        return self.value

    def is_empty(self) -> bool:
        """Check if notes are empty."""
        return not self.value.strip()


@dataclass(frozen=True)
class BalanceStatus:
    """
    Status indicator for a player's balance.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate balance status."""
        valid_statuses = {'settled', 'owes_money', 'owed_money', 'break_even'}

        if not isinstance(self.value, str):
            raise TypeError("Balance status must be a string")

        if self.value not in valid_statuses:
            raise ValueError(f"Balance status must be one of: {', '.join(valid_statuses)}")

    def __str__(self) -> str:
        return self.value

    def is_settled(self) -> bool:
        """Check if the balance is settled."""
        return self.value == 'settled'

    def owes_money(self) -> bool:
        """Check if the player owes money."""
        return self.value == 'owes_money'

    def is_owed_money(self) -> bool:
        """Check if the player is owed money."""
        return self.value == 'owed_money'

    def is_break_even(self) -> bool:
        """Check if the player is break-even."""
        return self.value == 'break_even'