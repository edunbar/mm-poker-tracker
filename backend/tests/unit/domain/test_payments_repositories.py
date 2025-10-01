"""Basic tests for payments domain repositories."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pytest
from abc import ABC
from unittest.mock import Mock
from datetime import datetime
from uuid import uuid4

# Import for coverage
import src.domain.payments.repositories
from src.domain.payments.repositories import PaymentRepository, PaymentBalanceRepository
from src.domain.payments.entities import PaymentTransaction, PlayerBalance
from src.domain.poker.value_objects import Money, PlayerId, GameId


class TestPaymentRepository:
    """Test PaymentRepository abstract interface."""

    def test_payment_repository_is_abstract(self):
        """Test that PaymentRepository is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            PaymentRepository()

    def test_payment_repository_interface(self):
        """Test PaymentRepository abstract methods exist."""
        # Verify the abstract methods exist
        assert hasattr(PaymentRepository, 'save_transaction')
        assert hasattr(PaymentRepository, 'get_transaction_by_id')
        assert hasattr(PaymentRepository, 'get_transactions_for_game')
        assert hasattr(PaymentRepository, 'get_transactions_for_player')
        assert hasattr(PaymentRepository, 'delete_transaction')

    def test_payment_repository_inheritance(self):
        """Test PaymentRepository inherits from ABC."""
        assert issubclass(PaymentRepository, ABC)


class TestPaymentBalanceRepository:
    """Test PaymentBalanceRepository abstract interface."""

    def test_balance_repository_is_abstract(self):
        """Test that PaymentBalanceRepository is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            PaymentBalanceRepository()

    def test_balance_repository_interface(self):
        """Test PaymentBalanceRepository abstract methods exist."""
        # Verify the abstract methods exist
        assert hasattr(PaymentBalanceRepository, 'get_balance')
        assert hasattr(PaymentBalanceRepository, 'get_all_balances_for_game')
        assert hasattr(PaymentBalanceRepository, 'save_balance')
        assert hasattr(PaymentBalanceRepository, 'update_balances_for_players')
        assert hasattr(PaymentBalanceRepository, 'delete_balance')

    def test_balance_repository_inheritance(self):
        """Test PaymentBalanceRepository inherits from ABC."""
        assert issubclass(PaymentBalanceRepository, ABC)


class MockPaymentRepository(PaymentRepository):
    """Mock implementation for testing."""

    def __init__(self):
        self.transactions = {}
        self.next_id = 1

    def save_transaction(self, transaction):
        transaction_id = f"txn-{self.next_id}"
        self.next_id += 1
        saved_transaction = transaction.with_transaction_id(transaction_id)
        self.transactions[transaction_id] = saved_transaction
        return saved_transaction

    def get_transaction_by_id(self, transaction_id):
        return self.transactions.get(transaction_id)

    def get_transactions_for_game(self, game_id):
        return [t for t in self.transactions.values() if t.game_id == game_id]

    def get_transactions_for_player(self, player_id, game_id):
        return [t for t in self.transactions.values()
                if t.involves_player(player_id) and t.game_id == game_id]

    def delete_transaction(self, transaction_id):
        if transaction_id in self.transactions:
            del self.transactions[transaction_id]
            return True
        return False


class MockPaymentBalanceRepository(PaymentBalanceRepository):
    """Mock implementation for testing."""

    def __init__(self):
        self.balances = {}

    def save_balance(self, balance):
        key = (str(balance.player_id), str(balance.game_id))
        self.balances[key] = balance
        return balance

    def get_balance(self, player_id, game_id):
        key = (str(player_id), str(game_id))
        return self.balances.get(key)

    def get_all_balances_for_game(self, game_id):
        return [b for b in self.balances.values() if b.game_id == game_id]

    def update_balances_for_players(self, game_id, player_ids):
        # Mock implementation - just mark as updated
        pass

    def delete_balance(self, player_id, game_id):
        key = (str(player_id), str(game_id))
        if key in self.balances:
            del self.balances[key]
            return True
        return False

    def get_balances_with_player_names(self, public_code):
        # Mock implementation
        return []


class TestMockImplementations:
    """Test that mock implementations work correctly."""

    def test_mock_payment_repository(self):
        """Test mock payment repository functionality."""
        repo = MockPaymentRepository()

        # Create a transaction
        transaction = PaymentTransaction.create_new(
            game_id=GameId(str(uuid4())),
            payer_id=PlayerId(str(uuid4())),
            recipient_id=PlayerId(str(uuid4())),
            amount=Money("50.00"),
            payment_date=datetime.now()
        )

        # Save transaction
        saved = repo.save_transaction(transaction)
        assert saved.transaction_id.startswith("txn-")

        # Find by ID
        found = repo.get_transaction_by_id(saved.transaction_id)
        assert found == saved

        # Find by game
        game_transactions = repo.get_transactions_for_game(transaction.game_id)
        assert len(game_transactions) == 1
        assert game_transactions[0] == saved

        # Find by player
        player_transactions = repo.get_transactions_for_player(transaction.payer_id, transaction.game_id)
        assert len(player_transactions) == 1
        assert player_transactions[0] == saved

    def test_mock_balance_repository(self):
        """Test mock balance repository functionality."""
        repo = MockPaymentBalanceRepository()

        # Create a balance
        player_id = PlayerId(str(uuid4()))
        game_id = GameId(str(uuid4()))
        balance = PlayerBalance.create_new(
            player_id=player_id,
            game_id=game_id,
            poker_net_winnings=Money("100.00")
        )

        # Save balance
        saved = repo.save_balance(balance)
        assert saved == balance

        # Find by player and game
        found = repo.get_balance(player_id, game_id)
        assert found == balance

        # Find by game
        game_balances = repo.get_all_balances_for_game(game_id)
        assert len(game_balances) == 1
        assert game_balances[0] == balance

        # Delete balance
        deleted = repo.delete_balance(player_id, game_id)
        assert deleted is True

        # Verify deletion
        found_after_delete = repo.get_balance(player_id, game_id)
        assert found_after_delete is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])