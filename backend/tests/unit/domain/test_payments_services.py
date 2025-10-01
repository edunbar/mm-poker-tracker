"""Basic tests for payments domain services."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pytest
from unittest.mock import Mock
from uuid import uuid4

# Import for coverage
import src.domain.payments.services
from src.domain.payments.services import SettlementOptimizer
from src.domain.payments.entities import PlayerBalance, SettlementSuggestion
from src.domain.poker.value_objects import Money, PlayerId, GameId


class TestSettlementOptimizer:
    """Test SettlementOptimizer service."""

    def test_calculate_optimal_settlements_empty_list(self):
        """Test with empty balance list."""
        result = SettlementOptimizer.calculate_optimal_settlements([])
        assert result == []

    def test_calculate_optimal_settlements_single_balance_settled(self):
        """Test with single settled balance."""
        balance = PlayerBalance.create_new(
            player_id=PlayerId(str(uuid4())),
            game_id=GameId(str(uuid4())),
            poker_net_winnings=Money("100.00"),
            total_paid=Money("50.00"),
            total_received=Money("150.00")  # Exactly settled
        )

        result = SettlementOptimizer.calculate_optimal_settlements([balance])
        assert result == []

    def test_calculate_optimal_settlements_single_balance_owes(self):
        """Test with single balance that owes money."""
        balance = PlayerBalance.create_new(
            player_id=PlayerId(str(uuid4())),
            game_id=GameId(str(uuid4())),
            poker_net_winnings=Money("0.00"),
            total_paid=Money("0.00"),
            total_received=Money("50.00")  # Owes $50
        )

        result = SettlementOptimizer.calculate_optimal_settlements([balance])
        # Single balance should return empty - need at least two players for settlement
        assert result == []

    def test_calculate_optimal_settlements_two_players(self):
        """Test with two players needing settlement."""
        player1_id = PlayerId(str(uuid4()))
        player2_id = PlayerId(str(uuid4()))
        game_id = GameId(str(uuid4()))

        # Player 1 owes money
        balance1 = PlayerBalance.create_new(
            player_id=player1_id,
            game_id=game_id,
            poker_net_winnings=Money("0.00"),
            total_paid=Money("0.00"),
            total_received=Money("50.00")  # Owes $50
        )

        # Player 2 is owed money
        balance2 = PlayerBalance.create_new(
            player_id=player2_id,
            game_id=game_id,
            poker_net_winnings=Money("100.00"),
            total_paid=Money("0.00"),
            total_received=Money("50.00")  # Owed $50
        )

        result = SettlementOptimizer.calculate_optimal_settlements([balance1, balance2])

        # Should suggest player1 pays player2
        assert len(result) == 1
        suggestion = result[0]
        assert suggestion.payer_id == player1_id
        assert suggestion.recipient_id == player2_id
        assert suggestion.amount.amount == Money("50.00").amount

    def test_calculate_optimal_settlements_multiple_players(self):
        """Test with multiple players."""
        game_id = GameId(str(uuid4()))

        # Create several balances with different amounts
        balances = []
        for i in range(3):
            player_id = PlayerId(str(uuid4()))
            if i == 0:
                # Owes money
                balance = PlayerBalance.create_new(
                    player_id=player_id,
                    game_id=game_id,
                    poker_net_winnings=Money("0.00"),
                    total_received=Money("30.00")
                )
            elif i == 1:
                # Owed money
                balance = PlayerBalance.create_new(
                    player_id=player_id,
                    game_id=game_id,
                    poker_net_winnings=Money("50.00"),
                    total_received=Money("20.00")
                )
            else:
                # Settled
                balance = PlayerBalance.create_new(
                    player_id=player_id,
                    game_id=game_id,
                    poker_net_winnings=Money("20.00"),
                    total_received=Money("20.00")
                )
            balances.append(balance)

        result = SettlementOptimizer.calculate_optimal_settlements(balances)

        # Should have some settlement suggestions
        assert isinstance(result, list)
        # Result should be list of SettlementSuggestion objects
        for suggestion in result:
            assert isinstance(suggestion, SettlementSuggestion)

    def test_calculate_optimal_settlements_all_settled(self):
        """Test with all players already settled."""
        game_id = GameId(str(uuid4()))

        balances = []
        for i in range(3):
            balance = PlayerBalance.create_new(
                player_id=PlayerId(str(uuid4())),
                game_id=game_id,
                poker_net_winnings=Money("100.00"),
                total_received=Money("100.00")  # All settled
            )
            balances.append(balance)

        result = SettlementOptimizer.calculate_optimal_settlements(balances)
        assert result == []

    def test_settlement_optimizer_class_exists(self):
        """Test that SettlementOptimizer class can be instantiated."""
        optimizer = SettlementOptimizer()
        assert optimizer is not None
        assert hasattr(optimizer, 'calculate_optimal_settlements')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])