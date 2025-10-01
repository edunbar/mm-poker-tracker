"""
Critical Financial Integrity Tests - Settlement Execution Verification

These tests prevent catastrophic settlement failures that could:
- Suggest payments that don't actually work
- Leave debts unresolved after settlements
- Create circular debt loops
- Lose money to rounding errors in optimization

All tests verify settlements achieve actual zero balances.
"""

import pytest
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import text
import itertools

from src.db.database import SessionLocal, engine
from src.db.models import Game, Player, PaymentTransaction, PaymentBalance, Session, SessionPlayerSummary
from src.services.payment_service_v2 import PaymentService


class TestSettlementExecution:
    """Critical tests for settlement suggestion accuracy and execution."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clean database before and after each test."""
        with engine.connect() as conn:
            # Clean up in dependency order
            conn.execute(text("DELETE FROM payment_transactions"))
            conn.execute(text("DELETE FROM payment_balances"))
            conn.execute(text("DELETE FROM session_player_summaries"))
            conn.execute(text("DELETE FROM sessions"))
            conn.execute(text("DELETE FROM game_players"))
            conn.execute(text("DELETE FROM players"))
            conn.execute(text("DELETE FROM games"))
            conn.commit()

        yield

        # Clean up after test
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM payment_transactions"))
            conn.execute(text("DELETE FROM payment_balances"))
            conn.execute(text("DELETE FROM session_player_summaries"))
            conn.execute(text("DELETE FROM sessions"))
            conn.execute(text("DELETE FROM game_players"))
            conn.execute(text("DELETE FROM players"))
            conn.execute(text("DELETE FROM games"))
            conn.commit()

    def create_test_game_with_players(self, num_players=3, poker_results=None):
        """Create a test game with players and session data."""
        if poker_results is None:
            # Default balanced poker results (sum = 0)
            poker_results = [5000, -2000, -3000]

        # Ensure poker results sum to zero
        assert sum(poker_results) == 0, f"Poker results must sum to 0, got {sum(poker_results)}"

        with SessionLocal() as db:
            # Create game
            game = Game(
                public_code=f"TEST{uuid4().hex[:6].upper()}",
                admin_code=f"admin-{uuid4()}",
                title="Settlement Test Game"
            )
            db.add(game)
            db.flush()

            # Create players
            players = []
            for i in range(num_players):
                player = Player(
                    external_id=f"player_{i}@test",
                    display_name=f"Player {i+1}"
                )
                db.add(player)
                players.append(player)

            db.flush()

            # Create session
            session = Session(
                game_id=game.id,
                external_id=f"session_{uuid4().hex[:8]}",
                game_number=1,
                started_at=datetime.now(timezone.utc),
                ended_at=datetime.now(timezone.utc)
            )
            db.add(session)
            db.flush()

            # Create session summaries with poker results
            for i, player in enumerate(players):
                summary = SessionPlayerSummary(
                    session_id=session.id,
                    player_id=player.id,
                    buy_in_sum=10000,
                    cash_out_sum=10000 + poker_results[i],
                    in_game=0,
                    net=poker_results[i],
                    names=[player.display_name]
                )
                db.add(summary)

            db.commit()
            return str(game.id), [str(p.id) for p in players]

    def execute_settlements(self, game_id, payment_service, max_iterations=10):
        """
        Execute settlement suggestions until all balances are zero.
        Returns number of iterations needed.
        """
        payment_date = datetime.now(timezone.utc)
        iterations = 0

        while iterations < max_iterations:
            suggestions = payment_service.get_settlement_suggestions(game_id)

            if not suggestions:
                # No more suggestions needed
                break

            # Execute all suggestions
            for i, suggestion in enumerate(suggestions):
                payment_service.record_payment(
                    game_id=game_id,
                    payer_id=suggestion.payer_id,
                    recipient_id=suggestion.recipient_id,
                    amount=suggestion.amount,
                    payment_date=payment_date,
                    payment_method="Settlement",
                    reference_id=f"settlement_{iterations}_{i}_{suggestion.payer_id[:8]}",
                    created_by="test"
                )

            iterations += 1

        return iterations

    def verify_settlement_completion(self, summaries, tolerance=Decimal("0.01")):
        """Verify all player balances are within tolerance of zero."""
        for summary in summaries:
            assert abs(summary.balance) <= tolerance, \
                f"Player {summary.player_name} balance ${summary.balance} not settled within ${tolerance}"

    def test_simple_settlement_execution(self, db_session):
        """
        CRITICAL: Basic settlement suggestions must achieve zero balances.
        """
        game_id, player_ids = self.create_test_game_with_players(3,
            poker_results=[5000, -2000, -3000])  # Alice owes $50, Bob owes $30, Charlie owed $80
        payment_service = PaymentService(db_session)

        # Get initial state
        initial_summaries = payment_service.get_payment_summary(game_id)

        # Verify someone owes money and someone is owed money
        balances = [s.balance for s in initial_summaries]
        assert any(b > 0 for b in balances), "No one is owed money"
        assert any(b < 0 for b in balances), "No one owes money"

        # Get and execute settlement suggestions
        suggestions = payment_service.get_settlement_suggestions(game_id)
        assert len(suggestions) > 0, "No settlement suggestions generated"

        # Execute settlements
        iterations = self.execute_settlements(game_id, payment_service)
        assert iterations <= 3, f"Too many iterations needed: {iterations}"

        # Verify settlement completion
        final_summaries = payment_service.get_payment_summary(game_id)
        self.verify_settlement_completion(final_summaries)

        # Verify money conservation
        total_paid = sum(s.total_paid for s in final_summaries)
        total_received = sum(s.total_received for s in final_summaries)
        assert total_paid == total_received, "Money not conserved during settlement"

    def test_complex_circular_debt_resolution(self, db_session):
        """
        CRITICAL: Complex circular debts (A→B→C→A) must be resolved optimally.
        """
        game_id, player_ids = self.create_test_game_with_players(4,
            poker_results=[15000, -5000, -7000, -3000])  # Complex debt structure
        payment_service = PaymentService(db_session)

        payment_date = datetime.now(timezone.utc)

        # Create circular debt scenario: A owes B, B owes C, C owes D, D owes A
        payment_service.record_payment(game_id, player_ids[1], player_ids[0], Decimal("80.00"), payment_date, "Setup", created_by="test")  # B pays A
        payment_service.record_payment(game_id, player_ids[2], player_ids[1], Decimal("60.00"), payment_date, "Setup", created_by="test")  # C pays B
        payment_service.record_payment(game_id, player_ids[3], player_ids[2], Decimal("40.00"), payment_date, "Setup", created_by="test")  # D pays C
        payment_service.record_payment(game_id, player_ids[0], player_ids[3], Decimal("20.00"), payment_date, "Setup", created_by="test")  # A pays D

        # Get pre-settlement state
        pre_settlement_summaries = payment_service.get_payment_summary(game_id)

        # Verify we have a complex debt structure
        non_zero_balances = [s for s in pre_settlement_summaries if abs(s.balance) > Decimal("0.01")]
        assert len(non_zero_balances) >= 3, "Need complex debt structure for this test"

        # Get and verify settlement suggestions
        suggestions = payment_service.get_settlement_suggestions(game_id)
        assert len(suggestions) > 0, "No settlement suggestions for circular debt"

        # The number of settlement suggestions should be optimal (n-1 for n players with debt)
        players_with_debt = len([s for s in pre_settlement_summaries if abs(s.balance) > Decimal("0.01")])
        expected_max_suggestions = players_with_debt - 1 if players_with_debt > 1 else 0

        assert len(suggestions) <= expected_max_suggestions, \
            f"Settlement not optimal: {len(suggestions)} suggestions for {players_with_debt} players with debt"

        # Execute settlements
        iterations = self.execute_settlements(game_id, payment_service)

        # Verify settlement completion
        final_summaries = payment_service.get_payment_summary(game_id)
        self.verify_settlement_completion(final_summaries)

        # Verify the settlement was efficient
        assert iterations <= 2, f"Circular debt resolution took too many iterations: {iterations}"

    def test_multi_player_settlement_optimization(self, db_session):
        """
        CRITICAL: 10+ players with complex debts must be settled optimally.
        """
        num_players = 10
        # Create complex but balanced poker results
        poker_results = [20000, 15000, 10000, 5000, 2000,  # Winners: $520 total
                        -8000, -12000, -15000, -17000, 0]  # Losers: -$520 total
        assert sum(poker_results) == 0

        game_id, player_ids = self.create_test_game_with_players(num_players, poker_results)
        payment_service = PaymentService(db_session)

        payment_date = datetime.now(timezone.utc)

        # Create complex payment web between players
        # Each player pays random amounts to other players
        import random
        random.seed(42)  # Deterministic for testing

        for i in range(30):  # 30 random payments to create complex debt web
            payer_idx = random.randint(0, num_players - 1)
            recipient_idx = random.randint(0, num_players - 1)

            while recipient_idx == payer_idx:
                recipient_idx = random.randint(0, num_players - 1)

            amount = Decimal(random.randint(500, 5000)) / 100  # $5-$50

            payment_service.record_payment(
                game_id, player_ids[payer_idx], player_ids[recipient_idx],
                amount, payment_date, "Complex", created_by="test"
            )

        # Get pre-settlement state
        pre_settlement_summaries = payment_service.get_payment_summary(game_id)
        players_with_debt = [s for s in pre_settlement_summaries if abs(s.balance) > Decimal("0.01")]

        # Get settlement suggestions
        suggestions = payment_service.get_settlement_suggestions(game_id)

        # For n players with non-zero balances, optimal solution needs at most n-1 payments
        max_optimal_payments = len(players_with_debt) - 1 if len(players_with_debt) > 1 else 0
        assert len(suggestions) <= max_optimal_payments, \
            f"Settlement not optimal: {len(suggestions)} payments for {len(players_with_debt)} players"

        # Calculate total settlement amount
        total_settlement_amount = sum(s.amount for s in suggestions)
        total_debt = sum(abs(s.balance) for s in players_with_debt if s.balance < 0)

        # Total settlement should equal total debt
        assert abs(total_settlement_amount - total_debt) < Decimal("0.01"), \
            f"Settlement amount ${total_settlement_amount} != total debt ${total_debt}"

        # Execute settlements
        iterations = self.execute_settlements(game_id, payment_service)

        # Verify settlement completion
        final_summaries = payment_service.get_payment_summary(game_id)
        self.verify_settlement_completion(final_summaries)

        # Performance check: should settle in very few iterations
        assert iterations <= 2, f"Complex settlement took too many iterations: {iterations}"

    def test_settlement_with_rounding_errors(self, db_session):
        """
        CRITICAL: Settlements must handle rounding properly without losing cents.
        """
        game_id, player_ids = self.create_test_game_with_players(3,
            poker_results=[333, -111, -222])  # Creates cent fractions when converted
        payment_service = PaymentService(db_session)

        payment_date = datetime.now(timezone.utc)

        # Add payments that create rounding challenges
        problematic_amounts = [
            Decimal("33.33"),
            Decimal("66.67"),  # These don't divide evenly
            Decimal("10.03"),  # Classic floating-point problem
            Decimal("7.77"),
        ]

        for i, amount in enumerate(problematic_amounts):
            payer_idx = i % len(player_ids)
            recipient_idx = (i + 1) % len(player_ids)

            payment_service.record_payment(
                game_id, player_ids[payer_idx], player_ids[recipient_idx],
                amount, payment_date, "Rounding", created_by="test"
            )

        # Get settlement suggestions
        suggestions = payment_service.get_settlement_suggestions(game_id)

        # Verify all suggestion amounts are valid (no negative, no self-payments)
        for suggestion in suggestions:
            assert suggestion.amount > 0, f"Invalid settlement amount: ${suggestion.amount}"
            assert suggestion.payer_id != suggestion.recipient_id, "Self-payment in settlement"

        # Execute settlements
        iterations = self.execute_settlements(game_id, payment_service)

        # Verify settlement completion with tight tolerance for rounding
        final_summaries = payment_service.get_payment_summary(game_id)
        self.verify_settlement_completion(final_summaries, tolerance=Decimal("0.01"))

        # Verify no money was lost to rounding
        total_paid = sum(s.total_paid for s in final_summaries)
        total_received = sum(s.total_received for s in final_summaries)
        assert total_paid == total_received, \
            f"Rounding error: paid=${total_paid}, received=${total_received}"

    def test_partial_settlement_execution(self, db_session):
        """
        CRITICAL: What happens if players only execute some settlement suggestions?
        System must remain consistent.
        """
        game_id, player_ids = self.create_test_game_with_players(4,
            poker_results=[10000, 5000, -7000, -8000])
        payment_service = PaymentService(db_session)

        payment_date = datetime.now(timezone.utc)

        # Get initial settlement suggestions
        initial_suggestions = payment_service.get_settlement_suggestions(game_id)
        assert len(initial_suggestions) >= 2, "Need multiple suggestions for partial execution test"

        # Execute only the first half of suggestions
        executed_count = len(initial_suggestions) // 2
        for i in range(executed_count):
            suggestion = initial_suggestions[i]
            payment_service.record_payment(
                game_id, suggestion.payer_id, suggestion.recipient_id,
                suggestion.amount, payment_date, "Partial", created_by="test"
            )

        # Get new settlement suggestions after partial execution
        remaining_suggestions = payment_service.get_settlement_suggestions(game_id)

        # Should still have suggestions for remaining debt
        partial_summaries = payment_service.get_payment_summary(game_id)
        remaining_debt_players = [s for s in partial_summaries if abs(s.balance) > Decimal("0.01")]

        if len(remaining_debt_players) > 1:
            assert len(remaining_suggestions) > 0, "No suggestions for remaining debt"

        # Execute remaining suggestions
        self.execute_settlements(game_id, payment_service)

        # Verify final settlement
        final_summaries = payment_service.get_payment_summary(game_id)
        self.verify_settlement_completion(final_summaries)

    def test_settlement_idempotency(self, db_session):
        """
        CRITICAL: Running settlement suggestions multiple times should not create extra payments.
        """
        game_id, player_ids = self.create_test_game_with_players(3)
        payment_service = PaymentService(db_session)

        # Get initial suggestions
        suggestions_1 = payment_service.get_settlement_suggestions(game_id)
        suggestions_2 = payment_service.get_settlement_suggestions(game_id)

        # Should be identical
        assert len(suggestions_1) == len(suggestions_2)
        for s1, s2 in zip(suggestions_1, suggestions_2):
            assert s1.payer_id == s2.payer_id
            assert s1.recipient_id == s2.recipient_id
            assert s1.amount == s2.amount

        # Execute suggestions once
        iterations = self.execute_settlements(game_id, payment_service)

        # Check if more suggestions exist (should be none)
        post_settlement_suggestions = payment_service.get_settlement_suggestions(game_id)
        final_summaries = payment_service.get_payment_summary(game_id)

        # If balances are settled, should have no suggestions
        settled_summaries = [s for s in final_summaries if abs(s.balance) <= Decimal("0.01")]
        if len(settled_summaries) == len(final_summaries):
            assert len(post_settlement_suggestions) == 0, "Suggestions exist after complete settlement"

    def test_settlement_optimization_vs_naive_approach(self, db_session):
        """
        CRITICAL: Settlement optimization should require fewer payments than naive approach.
        """
        game_id, player_ids = self.create_test_game_with_players(5,
            poker_results=[12000, 8000, -3000, -7000, -10000])
        payment_service = PaymentService(db_session)

        # Get initial state
        initial_summaries = payment_service.get_payment_summary(game_id)
        creditors = [s for s in initial_summaries if s.balance > Decimal("0.01")]
        debtors = [s for s in initial_summaries if s.balance < Decimal("-0.01")]

        # Naive approach: every debtor pays every creditor their proportional share
        naive_payment_count = len(debtors) * len(creditors)

        # Optimized approach
        suggestions = payment_service.get_settlement_suggestions(game_id)
        optimized_payment_count = len(suggestions)

        # Optimized should be significantly better for complex scenarios
        if len(creditors) > 1 and len(debtors) > 1:
            assert optimized_payment_count < naive_payment_count, \
                f"Optimization failed: {optimized_payment_count} vs naive {naive_payment_count}"

        # Theoretical optimal is at most n-1 payments for n players with non-zero balances
        players_with_balance = len(creditors) + len(debtors)
        theoretical_optimal = players_with_balance - 1

        assert optimized_payment_count <= theoretical_optimal, \
            f"Not optimal: {optimized_payment_count} payments for {players_with_balance} players"

        # Verify the optimized solution actually works
        iterations = self.execute_settlements(game_id, payment_service)
        final_summaries = payment_service.get_payment_summary(game_id)
        self.verify_settlement_completion(final_summaries)

    def test_edge_case_single_cent_balances(self, db_session):
        """
        CRITICAL: Handle edge case where balances are single cents.
        """
        game_id, player_ids = self.create_test_game_with_players(3,
            poker_results=[1, 1, -2])  # Tiny cent balances
        payment_service = PaymentService(db_session)

        suggestions = payment_service.get_settlement_suggestions(game_id)

        # Verify suggestions handle cents properly
        for suggestion in suggestions:
            assert suggestion.amount >= Decimal("0.01"), \
                f"Suggestion amount too small: ${suggestion.amount}"

        # Execute and verify
        if suggestions:  # Only if there are suggestions (might be filtered out if < 1 cent)
            iterations = self.execute_settlements(game_id, payment_service)
            final_summaries = payment_service.get_payment_summary(game_id)
            self.verify_settlement_completion(final_summaries)

    def test_settlement_performance_benchmark(self, db_session):
        """
        CRITICAL: Settlement calculation and execution must complete in reasonable time.
        """
        import time

        # Large game with many players
        num_players = 20
        # Create large balanced poker results
        poker_results = ([i * 1000 for i in range(1, 11)] +  # Winners: $1k to $10k
                        [-sum(range(1000, 11000, 1000)) // 10] * 10)  # Losers: split the loss

        # Ensure balance
        while sum(poker_results) != 0:
            poker_results[-1] += -sum(poker_results)

        game_id, player_ids = self.create_test_game_with_players(num_players, poker_results)
        payment_service = PaymentService(db_session)

        # Measure settlement suggestion time
        start_time = time.time()
        suggestions = payment_service.get_settlement_suggestions(game_id)
        suggestion_time = time.time() - start_time

        # Should complete in under 1 second for 20 players
        assert suggestion_time < 1.0, f"Settlement calculation too slow: {suggestion_time:.2f}s"

        # Measure execution time
        start_time = time.time()
        iterations = self.execute_settlements(game_id, payment_service)
        execution_time = time.time() - start_time

        # Should complete execution in under 5 seconds
        assert execution_time < 5.0, f"Settlement execution too slow: {execution_time:.2f}s"

        # Verify correctness
        final_summaries = payment_service.get_payment_summary(game_id)
        self.verify_settlement_completion(final_summaries)

        print(f"Performance: {len(suggestions)} suggestions in {suggestion_time:.3f}s, "
              f"executed in {execution_time:.3f}s over {iterations} iterations")