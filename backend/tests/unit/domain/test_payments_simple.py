"""Simple tests for payments domain to establish coverage."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pytest
from uuid import uuid4
from datetime import datetime

# Import for coverage - try direct import
import src.domain.payments.value_objects as payment_vo
import src.domain.payments.entities as payment_entities

def test_simple_value_objects():
    """Test simple value object creation."""
    # TransactionId
    valid_uuid = str(uuid4())
    tid = payment_vo.TransactionId(valid_uuid)
    assert str(tid) == valid_uuid

    # PaymentMethod
    method = payment_vo.PaymentMethod("Cash")
    assert str(method) == "Cash"

    # BalanceStatus with correct values
    status = payment_vo.BalanceStatus("settled")
    assert str(status) == "settled"
    assert status.is_settled() is True
    assert status.owes_money() is False

    status2 = payment_vo.BalanceStatus("owes_money")
    assert status2.owes_money() is True
    assert status2.is_settled() is False

    print("✅ Payments value objects working")

def test_transaction_id_validation():
    """Test TransactionId validation."""
    # Valid UUID
    valid_uuid = str(uuid4())
    tid = payment_vo.TransactionId(valid_uuid)
    assert tid.value == valid_uuid

    # Invalid UUID
    with pytest.raises(ValueError, match="Invalid transaction ID UUID format"):
        payment_vo.TransactionId("not-a-uuid")

    # Empty string
    with pytest.raises(ValueError, match="Transaction ID cannot be empty"):
        payment_vo.TransactionId("")

def test_payment_method_validation():
    """Test PaymentMethod validation."""
    # Valid method
    method = payment_vo.PaymentMethod("Venmo")
    assert method.value == "Venmo"

    # With whitespace
    method2 = payment_vo.PaymentMethod("  Cash  ")
    assert method2.value == "Cash"  # Should be trimmed

    # Non-string type
    with pytest.raises(TypeError, match="Payment method must be a string"):
        payment_vo.PaymentMethod(123)

def test_balance_status_methods():
    """Test BalanceStatus methods."""
    # Test all valid statuses
    settled = payment_vo.BalanceStatus("settled")
    assert settled.is_settled() is True
    assert settled.owes_money() is False
    assert settled.is_owed_money() is False
    assert settled.is_break_even() is False

    owes = payment_vo.BalanceStatus("owes_money")
    assert owes.owes_money() is True
    assert owes.is_settled() is False

    owed = payment_vo.BalanceStatus("owed_money")
    assert owed.is_owed_money() is True
    assert owed.is_settled() is False

    even = payment_vo.BalanceStatus("break_even")
    assert even.is_break_even() is True
    assert even.is_settled() is False

if __name__ == "__main__":
    test_simple_value_objects()
    test_transaction_id_validation()
    test_payment_method_validation()
    test_balance_status_methods()
    print("✅ All payments tests passed")