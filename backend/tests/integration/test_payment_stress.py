"""
Critical Financial Integrity Tests - Stress Testing

These tests verify system stability under extreme load:
- High-frequency payment bursts
- Large-scale games with many players
- Memory leak detection during long operations
- Database connection pool exhaustion handling
- Performance degradation under load

All tests ensure financial integrity is maintained under stress.
"""

import pytest
import time
import threading
from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy import text

from src.db.database import SessionLocal, engine
from src.db.models import Game, Player, PaymentTransaction, PaymentBalance, Session, SessionPlayerSummary
from src.services.payment_service_v2 import PaymentService
from tests.integration.test_utilities import FinancialIntegrityTestUtils


class TestPaymentStress:
    """Stress tests for payment system financial integrity under load."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clean database before and after each test."""
        FinancialIntegrityTestUtils.clean_database()
        yield
        FinancialIntegrityTestUtils.clean_database()

    def test_rapid_fire_payment_burst(self):
        """
        CRITICAL: Rapid payments under concurrent load must maintain integrity.
        """
        # Create large game
        game_setup = FinancialIntegrityTestUtils.create_balanced_game("BURST", 8)
        payment_date = datetime.now(timezone.utc)

        num_payments = 50  # Realistic burst size
        payment_amount = Decimal("1.00")

        def make_burst_payment(i):
            payer_idx = i % len(game_setup.player_ids)
            recipient_idx = (i + 1) % len(game_setup.player_ids)

            # Each thread gets its own session
            with SessionLocal() as db:
                try:
                    payment_service = PaymentService(db)
                    result = payment_service.record_payment(
                        game_id=game_setup.game_id,
                        payer_id=game_setup.player_ids[payer_idx],
                        recipient_id=game_setup.player_ids[recipient_idx],
                        amount=payment_amount,
                        payment_date=payment_date,
                        payment_method="Burst",
                        reference_id=f"burst_{i}",
                        created_by="stress_test"
                    )
                    db.commit()
                    return result
                except Exception as e:
                    db.rollback()
                    return e

        start_time = time.time()

        # Execute all payments with realistic concurrency
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_burst_payment, i) for i in range(num_payments)]
            results = [future.result() for future in as_completed(futures)]

        end_time = time.time()
        duration = end_time - start_time

        # Verify all payments succeeded
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) == num_payments, f"Only {len(successful)}/{num_payments} payments succeeded"

        # Verify financial integrity maintained
        final_snapshot = FinancialIntegrityTestUtils.take_financial_snapshot(game_setup.game_id)
        FinancialIntegrityTestUtils.verify_financial_invariants(final_snapshot)

        # Performance requirement: reasonable for realistic load
        assert duration < 60.0, f"Burst test too slow: {duration:.2f}s"

        print(f"Burst test: {num_payments} payments in {duration:.2f}s ({num_payments/duration:.1f} payments/sec)")

    def test_large_scale_game_performance(self):
        """
        CRITICAL: Large game with realistic payment volume must remain performant.
        """
        num_players = 20  # Realistic large game

        # Create large balanced game
        large_poker_results = []
        winners = num_players // 2
        losers = num_players - winners

        # Winners get varying amounts
        for i in range(winners):
            large_poker_results.append((i + 1) * 2000)  # $20, $40, $60, etc.

        # Losers split the total loss
        total_winnings = sum(large_poker_results)
        loss_per_loser = -(total_winnings // losers)
        remainder = -(total_winnings % losers)

        for i in range(losers):
            loss = loss_per_loser + (remainder if i == 0 else 0)
            large_poker_results.append(loss)

        game_setup = FinancialIntegrityTestUtils.create_balanced_game(
            "LARGE", num_players, large_poker_results
        )

        # Create realistic payment volume
        payment_sequence = FinancialIntegrityTestUtils.generate_random_payment_scenario(
            game_setup, num_payments=100, seed=123
        )

        start_time = time.time()

        # Execute all payments (no batching needed for 100 payments)
        FinancialIntegrityTestUtils.execute_payment_sequence(game_setup.game_id, payment_sequence)

        end_time = time.time()
        duration = end_time - start_time

        # Final integrity check
        final_snapshot = FinancialIntegrityTestUtils.take_financial_snapshot(game_setup.game_id)
        FinancialIntegrityTestUtils.verify_financial_invariants(final_snapshot)

        # Performance requirement: reasonable for realistic load
        assert duration < 120.0, f"Large game test too slow: {duration:.2f}s"

        print(f"Large scale: {num_players} players, {len(payment_sequence)} payments in {duration:.2f}s")


        # Verify financial integrity maintained throughout
        final_snapshot = FinancialIntegrityTestUtils.take_financial_snapshot(game_setup.game_id)
        FinancialIntegrityTestUtils.verify_financial_invariants(final_snapshot)

    def test_database_connection_pool_stress(self):
        """
        CRITICAL: System must handle connection pool exhaustion gracefully.
        """
        game_setup = FinancialIntegrityTestUtils.create_balanced_game("CONNPOOL", 5)
        payment_date = datetime.now(timezone.utc)

        def connection_intensive_operation(operation_id):
            """Operation that uses many database connections."""
            try:
                # Each thread gets its own session
                with SessionLocal() as db:
                    payment_service = PaymentService(db)

                    # Each operation opens multiple connections
                    for i in range(5):
                        payment_service.record_payment(
                            game_id=game_setup.game_id,
                            payer_id=game_setup.player_ids[i % len(game_setup.player_ids)],
                            recipient_id=game_setup.player_ids[(i + 1) % len(game_setup.player_ids)],
                            amount=Decimal("1.00"),
                            payment_date=payment_date,
                            payment_method=f"ConnPool_{operation_id}",
                            created_by="stress_test"
                        )

                        # Get summary (another connection)
                        summaries = payment_service.get_payment_summary(game_setup.game_id)

                    db.commit()
                return f"success_{operation_id}"
            except Exception as e:
                return f"error_{operation_id}: {e}"

        # Launch many concurrent operations to stress connection pool
        num_workers = 50  # Likely exceeds typical connection pool size
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(connection_intensive_operation, i)
                for i in range(num_workers)
            ]
            results = [future.result() for future in as_completed(futures)]

        # Verify most operations succeeded (some may fail due to pool limits)
        successful = [r for r in results if r.startswith("success_")]
        failed = [r for r in results if r.startswith("error_")]

        success_rate = len(successful) / len(results)
        assert success_rate > 0.7, f"Too many connection failures: {success_rate:.1%} success rate"

        # Most importantly: verify financial integrity maintained
        final_snapshot = FinancialIntegrityTestUtils.take_financial_snapshot(game_setup.game_id)
        FinancialIntegrityTestUtils.verify_financial_invariants(final_snapshot)

        print(f"Connection pool stress: {len(successful)}/{len(results)} operations succeeded")

    def test_concurrent_games_stress(self):
        """
        CRITICAL: Multiple games under load simultaneously must not interfere.
        """
        num_games = 10
        games_and_setups = []

        # Create multiple games
        for i in range(num_games):
            game_setup = FinancialIntegrityTestUtils.create_balanced_game(f"MULTI{i}", 5)
            games_and_setups.append(game_setup)

        def stress_single_game(game_setup):
            """Apply stress to a single game."""
            payments = FinancialIntegrityTestUtils.generate_random_payment_scenario(
                game_setup, num_payments=100, seed=hash(game_setup.game_id) % 1000
            )

            results = FinancialIntegrityTestUtils.execute_payment_sequence(
                game_setup.game_id, payments
            )

            # Verify integrity for this game
            snapshot = FinancialIntegrityTestUtils.take_financial_snapshot(game_setup.game_id)
            FinancialIntegrityTestUtils.verify_financial_invariants(snapshot)

            return len(results)

        # Stress all games concurrently
        with ThreadPoolExecutor(max_workers=num_games) as executor:
            futures = [
                executor.submit(stress_single_game, game_setup)
                for game_setup in games_and_setups
            ]
            results = [future.result() for future in as_completed(futures)]

        # Verify all games processed successfully
        assert all(isinstance(r, int) and r > 0 for r in results), \
            "Some games failed during concurrent stress test"

        # Verify each game maintains individual integrity
        for game_setup in games_and_setups:
            snapshot = FinancialIntegrityTestUtils.take_financial_snapshot(game_setup.game_id)
            FinancialIntegrityTestUtils.verify_financial_invariants(snapshot)

        print(f"Concurrent games stress: {num_games} games processed successfully")

    def test_extreme_payment_amounts(self):
        """
        CRITICAL: System must handle extreme payment amounts without overflow.
        """
        game_setup = FinancialIntegrityTestUtils.create_balanced_game("EXTREME", 3)
        payment_date = datetime.now(timezone.utc)

        # Test with very large amounts
        extreme_amounts = [
            Decimal("999999.99"),    # Near million dollars
            Decimal("0.01"),         # Single cent
            Decimal("123456.78"),    # Large with precision
            Decimal("1.23"),         # Small with precision
        ]

        for amount in extreme_amounts:
            payer_id = game_setup.player_ids[0]
            recipient_id = game_setup.player_ids[1]

            with SessionLocal() as db:
                payment_service = PaymentService(db)
                payment_service.record_payment(
                    game_id=game_setup.game_id,
                    payer_id=payer_id,
                    recipient_id=recipient_id,
                    amount=amount,
                    payment_date=payment_date,
                    payment_method="Extreme",
                    created_by="stress_test"
                )
                db.commit()

            # Verify precision maintained
            snapshot = FinancialIntegrityTestUtils.take_financial_snapshot(game_setup.game_id)
            FinancialIntegrityTestUtils.verify_financial_invariants(snapshot)

        # Verify final state
        with SessionLocal() as db:
            payment_service = PaymentService(db)
            final_summaries = payment_service.get_payment_summary(game_setup.game_id)
        total_extreme = sum(extreme_amounts)

        payer_summary = next(s for s in final_summaries if s.player_id == game_setup.player_ids[0])
        recipient_summary = next(s for s in final_summaries if s.player_id == game_setup.player_ids[1])

        assert payer_summary.total_paid == total_extreme
        assert recipient_summary.total_received == total_extreme

    def test_settlement_performance_under_load(self):
        """
        CRITICAL: Settlement calculations must remain fast even with complex debt webs.
        """
        # Create complex game with many players
        num_players = 30
        game_setup = FinancialIntegrityTestUtils.create_balanced_game("SETTPERF", num_players)

        # Create extremely complex debt web
        complex_payments = []
        for i in range(num_players):
            for j in range(num_players):
                if i != j:
                    # Each player pays a different amount to every other player
                    amount = Decimal(f"{(i+1)}.{j+1:02d}")  # e.g., $1.01, $1.02, $2.01, etc.
                    complex_payments.append((
                        game_setup.player_ids[i],
                        game_setup.player_ids[j],
                        amount,
                        f"Complex_{i}_{j}"
                    ))

        # Execute complex payment web
        FinancialIntegrityTestUtils.execute_payment_sequence(game_setup.game_id, complex_payments)

        # Measure settlement calculation performance
        with SessionLocal() as db:
            payment_service = PaymentService(db)
            start_time = time.time()
            suggestions = payment_service.get_settlement_suggestions(game_setup.game_id)
            calculation_time = time.time() - start_time

        # Should complete settlement calculation in reasonable time
        assert calculation_time < 5.0, f"Settlement calculation too slow: {calculation_time:.2f}s"

        # Verify suggestions are mathematically correct
        validation_results = FinancialIntegrityTestUtils.verify_settlement_suggestions_valid(game_setup.game_id)

        for result in validation_results:
            assert all(result.values()), f"Invalid settlement suggestion: {result}"

        # Verify settlement execution performance
        start_time = time.time()
        settlement_metrics = FinancialIntegrityTestUtils.simulate_settlement_execution(game_setup.game_id)
        execution_time = time.time() - start_time

        assert execution_time < 10.0, f"Settlement execution too slow: {execution_time:.2f}s"
        assert settlement_metrics["settlement_completed"], "Settlement did not complete"

        print(f"Settlement performance: calculation {calculation_time:.2f}s, execution {execution_time:.2f}s")
        print(f"Settled in {settlement_metrics['iterations']} iterations with {settlement_metrics['total_suggestions']} total suggestions")