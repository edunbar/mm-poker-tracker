"""Comprehensive tests for payments domain value objects."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pytest
from uuid import uuid4

# Import for coverage
import src.domain.payments.value_objects
from src.domain.payments.value_objects import (
    TransactionId,
    PaymentMethod,
    PaymentReference,
    PaymentNotes,
    BalanceStatus
)


class TestTransactionId:
    """Test TransactionId value object."""

    def test_valid_transaction_id(self):
        """Test creating valid transaction ID."""
        valid_uuid = str(uuid4())
        transaction_id = TransactionId(valid_uuid)

        assert transaction_id.value == valid_uuid
        assert str(transaction_id) == valid_uuid

    def test_transaction_id_empty_string(self):
        """Test transaction ID with empty string."""
        with pytest.raises(ValueError, match="Transaction ID cannot be empty"):
            TransactionId("")

    def test_transaction_id_whitespace_only(self):
        """Test transaction ID with whitespace only."""
        with pytest.raises(ValueError, match="Transaction ID cannot be empty"):
            TransactionId("   ")

    def test_transaction_id_non_string(self):
        """Test transaction ID with non-string type."""
        with pytest.raises(ValueError, match="Transaction ID cannot be empty"):
            TransactionId(None)

    def test_transaction_id_invalid_uuid_format(self):
        """Test transaction ID with invalid UUID format."""
        with pytest.raises(ValueError, match="Invalid transaction ID UUID format"):
            TransactionId("not-a-valid-uuid")

    def test_transaction_id_immutable(self):
        """Test transaction ID is immutable."""
        transaction_id = TransactionId(str(uuid4()))

        with pytest.raises(AttributeError):
            transaction_id.value = "new-value"

    def test_transaction_id_equality(self):
        """Test transaction ID equality."""
        uuid_str = str(uuid4())
        tid1 = TransactionId(uuid_str)
        tid2 = TransactionId(uuid_str)
        tid3 = TransactionId(str(uuid4()))

        assert tid1 == tid2
        assert tid1 != tid3


class TestPaymentMethod:
    """Test PaymentMethod value object."""

    def test_valid_payment_method(self):
        """Test creating valid payment method."""
        method = PaymentMethod("Cash")
        assert method.value == "Cash"
        assert str(method) == "Cash"

    def test_payment_method_normalization(self):
        """Test payment method whitespace normalization."""
        method = PaymentMethod("  Venmo  ")
        assert method.value == "Venmo"

    def test_payment_method_non_string(self):
        """Test payment method with non-string type."""
        with pytest.raises(TypeError, match="Payment method must be a string"):
            PaymentMethod(123)

    def test_payment_method_empty_after_normalization(self):
        """Test payment method empty after normalization."""
        with pytest.raises(ValueError, match="Payment method cannot be empty"):
            PaymentMethod("   ")

    def test_payment_method_valid_methods(self):
        """Test various valid payment methods."""
        valid_methods = ["Cash", "Venmo", "Zelle", "PayPal", "Check"]

        for method_name in valid_methods:
            method = PaymentMethod(method_name)
            assert method.value == method_name

    def test_payment_method_case_sensitivity(self):
        """Test payment method is case sensitive."""
        method1 = PaymentMethod("Cash")
        method2 = PaymentMethod("cash")

        assert method1 != method2
        assert method1.value == "Cash"
        assert method2.value == "cash"

    def test_payment_method_immutable(self):
        """Test payment method is immutable."""
        method = PaymentMethod("Cash")

        with pytest.raises(AttributeError):
            method.value = "Venmo"


class TestPaymentReference:
    """Test PaymentReference value object."""

    def test_valid_payment_reference(self):
        """Test creating valid payment reference."""
        ref = PaymentReference("REF123456")
        assert ref.value == "REF123456"
        assert str(ref) == "REF123456"

    def test_payment_reference_normalization(self):
        """Test payment reference whitespace normalization."""
        ref = PaymentReference("  REF123  ")
        assert ref.value == "REF123"

    def test_payment_reference_non_string(self):
        """Test payment reference with non-string type."""
        with pytest.raises(TypeError, match="Payment reference must be a string"):
            PaymentReference(123)

    def test_payment_reference_empty_after_normalization(self):
        """Test payment reference empty after normalization."""
        with pytest.raises(ValueError, match="Payment reference cannot be empty"):
            PaymentReference("   ")

    def test_payment_reference_length_limit(self):
        """Test payment reference length validation."""
        # Valid length
        ref = PaymentReference("A" * 100)
        assert len(ref.value) == 100

        # Too long
        with pytest.raises(ValueError, match="Payment reference cannot exceed 100 characters"):
            PaymentReference("A" * 101)

    def test_payment_reference_immutable(self):
        """Test payment reference is immutable."""
        ref = PaymentReference("REF123")

        with pytest.raises(AttributeError):
            ref.value = "REF456"


class TestPaymentNotes:
    """Test PaymentNotes value object."""

    def test_valid_payment_notes(self):
        """Test creating valid payment notes."""
        notes = PaymentNotes("Payment for poker night")
        assert notes.value == "Payment for poker night"
        assert str(notes) == "Payment for poker night"

    def test_payment_notes_normalization(self):
        """Test payment notes whitespace normalization."""
        notes = PaymentNotes("  Payment details  ")
        assert notes.value == "Payment details"

    def test_payment_notes_non_string(self):
        """Test payment notes with non-string type."""
        with pytest.raises(TypeError, match="Payment notes must be a string"):
            PaymentNotes(123)

    def test_payment_notes_empty_after_normalization(self):
        """Test payment notes empty after normalization."""
        with pytest.raises(ValueError, match="Payment notes cannot be empty"):
            PaymentNotes("   ")

    def test_payment_notes_length_limit(self):
        """Test payment notes length validation."""
        # Valid length
        notes = PaymentNotes("A" * 500)
        assert len(notes.value) == 500

        # Too long
        with pytest.raises(ValueError, match="Payment notes cannot exceed 500 characters"):
            PaymentNotes("A" * 501)

    def test_payment_notes_multiline(self):
        """Test payment notes with multiline text."""
        multiline_notes = "Line 1\nLine 2\nLine 3"
        notes = PaymentNotes(multiline_notes)
        assert notes.value == multiline_notes

    def test_payment_notes_immutable(self):
        """Test payment notes is immutable."""
        notes = PaymentNotes("Test notes")

        with pytest.raises(AttributeError):
            notes.value = "New notes"


class TestBalanceStatus:
    """Test BalanceStatus value object."""

    def test_valid_balance_status(self):
        """Test creating valid balance status."""
        status = BalanceStatus("PENDING")
        assert status.value == "PENDING"
        assert str(status) == "PENDING"

    def test_balance_status_normalization(self):
        """Test balance status normalization."""
        status = BalanceStatus("  pending  ")
        assert status.value == "PENDING"  # Should be normalized to uppercase

    def test_balance_status_non_string(self):
        """Test balance status with non-string type."""
        with pytest.raises(TypeError, match="Balance status must be a string"):
            BalanceStatus(123)

    def test_balance_status_empty(self):
        """Test balance status with empty string."""
        with pytest.raises(ValueError, match="Balance status cannot be empty"):
            BalanceStatus("")

    def test_balance_status_valid_values(self):
        """Test valid balance status values."""
        valid_statuses = ["PENDING", "CONFIRMED", "DISPUTED", "SETTLED"]

        for status_value in valid_statuses:
            status = BalanceStatus(status_value)
            assert status.value == status_value

    def test_balance_status_invalid_value(self):
        """Test invalid balance status value."""
        with pytest.raises(ValueError, match="Invalid balance status"):
            BalanceStatus("INVALID")

    def test_balance_status_case_normalization(self):
        """Test balance status case normalization."""
        status = BalanceStatus("pending")
        assert status.value == "PENDING"

        status = BalanceStatus("Confirmed")
        assert status.value == "CONFIRMED"

    def test_balance_status_immutable(self):
        """Test balance status is immutable."""
        status = BalanceStatus("PENDING")

        with pytest.raises(AttributeError):
            status.value = "CONFIRMED"

    def test_balance_status_equality(self):
        """Test balance status equality."""
        status1 = BalanceStatus("PENDING")
        status2 = BalanceStatus("pending")  # Should normalize to same value
        status3 = BalanceStatus("CONFIRMED")

        assert status1 == status2
        assert status1 != status3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])