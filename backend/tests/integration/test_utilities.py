"""
Financial Integrity Test Utilities

Common utilities and fixtures for financial integrity testing.
These utilities ensure consistent test data and verification methods.
"""

from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
from sqlalchemy import text

from src.db.database import SessionLocal, engine
from src.db.models import Game, Player, PaymentTransaction, PaymentBalance, Session, SessionPlayerSummary
from src.services.payment_service_v2 import PaymentService


@dataclass
class TestGameSetup:
    """Container for test game data."""
    game_id: str
    player_ids: List[str]
    player_names: List[str]
    poker_results: List[int]  # In cents


@dataclass
class FinancialSnapshot:
    """Snapshot of financial state for verification."""
    total_paid: Decimal
    total_received: Decimal
    total_poker_winnings: Decimal
    total_balances: Decimal
    player_count: int
    payment_count: int


class FinancialIntegrityTestUtils:
    """Utilities for financial integrity testing."""

    @staticmethod
    def clean_database():
        """Clean all financial data from database."""
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

    @staticmethod
    def create_balanced_game(
        game_suffix: str,
        num_players: int = 3,
        poker_results: List[int] = None,
        base_buyin: int = 10000
    ) -> TestGameSetup:
        """
        Create a test game with balanced poker results.

        Args:
            game_suffix: Unique suffix for game identification
            num_players: Number of players to create
            poker_results: Poker results in cents (must sum to 0)
            base_buyin: Base buy-in amount in cents

        Returns:
            TestGameSetup with game and player data
        """
        if poker_results is None:
            # Generate balanced results
            if num_players == 3:
                poker_results = [5000, -2000, -3000]
            elif num_players == 4:
                poker_results = [7000, 2000, -4000, -5000]
            elif num_players == 5:
                poker_results = [8000, 3000, 1000, -6000, -6000]
            else:
                # Generate simple balanced results
                winners = num_players // 2
                losers = num_players - winners
                win_amount = 1000 * losers  # Each winner gets 1000 * number of losers
                lose_amount = -1000 * winners  # Each loser loses 1000 * number of winners

                poker_results = ([win_amount] * winners + [lose_amount] * losers)

        # Ensure balance
        if sum(poker_results) != 0:
            adjustment = -sum(poker_results)
            poker_results[0] += adjustment

        assert sum(poker_results) == 0, f"Poker results must sum to 0, got {sum(poker_results)}"
        assert len(poker_results) == num_players, "Poker results count must match player count"

        with SessionLocal() as db:
            # Create game
            game = Game(
                public_code=f"TEST{game_suffix}",
                admin_code=f"admin-{game_suffix}-{uuid4()}",
                title=f"Test Game {game_suffix}"
            )
            db.add(game)
            db.flush()

            # Create players
            players = []
            player_names = []
            for i in range(num_players):
                player = Player(
                    external_id=f"player_{i}_{game_suffix}@test",
                    display_name=f"Player {i+1}"
                )
                db.add(player)
                players.append(player)
                player_names.append(player.display_name)

            db.flush()

            # Create session
            session = Session(
                game_id=game.id,
                external_id=f"session_{game_suffix}_{uuid4().hex[:8]}",
                game_number=1,
                started_at=datetime.now(timezone.utc),
                ended_at=datetime.now(timezone.utc)
            )
            db.add(session)
            db.flush()

            # Create session summaries
            for i, player in enumerate(players):
                summary = SessionPlayerSummary(
                    session_id=session.id,
                    player_id=player.id,
                    buy_in_sum=base_buyin,
                    cash_out_sum=base_buyin + poker_results[i],
                    in_game=0,
                    net=poker_results[i],
                    names=[player.display_name]
                )
                db.add(summary)

            db.commit()

            return TestGameSetup(
                game_id=str(game.id),
                player_ids=[str(p.id) for p in players],
                player_names=player_names,
                poker_results=poker_results
            )

    @staticmethod
    def take_financial_snapshot(game_id: str) -> FinancialSnapshot:
        """Take a snapshot of current financial state."""
        with SessionLocal() as db:
            payment_service = PaymentService(db)
            summaries = payment_service.get_payment_summary(game_id)

            total_paid = sum(s.total_paid for s in summaries)
            total_received = sum(s.total_received for s in summaries)
            total_poker_winnings = sum(s.poker_net_winnings for s in summaries)
            total_balances = sum(s.balance for s in summaries)

            payment_count = db.query(PaymentTransaction).filter(
                PaymentTransaction.game_id == game_id
            ).count()

            return FinancialSnapshot(
                total_paid=total_paid,
                total_received=total_received,
                total_poker_winnings=total_poker_winnings,
                total_balances=total_balances,
                player_count=len(summaries),
                payment_count=payment_count
            )

    @staticmethod
    def verify_financial_invariants(snapshot: FinancialSnapshot, tolerance: Decimal = Decimal("0.01")):
        """
        Verify core financial invariants.

        Args:
            snapshot: Financial snapshot to verify
            tolerance: Acceptable tolerance for floating-point comparisons

        Raises:
            AssertionError: If any invariant is violated
        """
        # Money conservation: total paid = total received
        assert snapshot.total_paid == snapshot.total_received, \
            f"Money creation/destruction: paid=${snapshot.total_paid}, received=${snapshot.total_received}"

        # Zero-sum poker: poker winnings sum to zero
        assert abs(snapshot.total_poker_winnings) <= tolerance, \
            f"Poker results not zero-sum: total=${snapshot.total_poker_winnings}"

        # Zero-sum balances: all balances sum to zero
        assert abs(snapshot.total_balances) <= tolerance, \
            f"Player balances don't sum to zero: total=${snapshot.total_balances}"

    @staticmethod
    def execute_payment_sequence(
        game_id: str,
        payments: List[Tuple[str, str, Decimal, str]]
    ) -> List[PaymentTransaction]:
        """
        Execute a sequence of payments and return results.

        Args:
            game_id: Game to make payments in
            payments: List of (payer_id, recipient_id, amount, method) tuples

        Returns:
            List of created PaymentTransaction objects
        """
        # V2 PaymentService requires a session - create and manage one
        with SessionLocal() as db_session:
            payment_service = PaymentService(db_session)
            payment_date = datetime.now(timezone.utc)
            results = []

            for payer_id, recipient_id, amount, method in payments:
                payment = payment_service.record_payment(
                    game_id=game_id,
                    payer_id=payer_id,
                    recipient_id=recipient_id,
                    amount=amount,
                    payment_date=payment_date,
                    payment_method=method,
                    created_by="test"
                )
                results.append(payment)

            db_session.commit()

        return results

    @staticmethod
    def verify_settlement_suggestions_valid(game_id: str) -> List[Dict[str, Any]]:
        """
        Verify settlement suggestions are mathematically correct.

        Returns:
            List of validation results
        """
        with SessionLocal() as db:
            payment_service = PaymentService(db)
            summaries = payment_service.get_payment_summary(game_id)
            suggestions = payment_service.get_settlement_suggestions(game_id)

        validation_results = []

        # Check that suggestions only involve players with non-zero balances
        players_with_debt = {s.player_id for s in summaries if abs(s.balance) > Decimal("0.01")}

        for suggestion in suggestions:
            result = {
                "suggestion": suggestion,
                "valid_payer": suggestion.payer_id in players_with_debt,
                "valid_recipient": suggestion.recipient_id in players_with_debt,
                "positive_amount": suggestion.amount > 0,
                "not_self_payment": suggestion.payer_id != suggestion.recipient_id
            }

            # Check that payer actually owes money
            payer_summary = next((s for s in summaries if s.player_id == suggestion.payer_id), None)
            result["payer_owes_money"] = payer_summary and payer_summary.balance < -Decimal("0.01")

            # Check that recipient is owed money
            recipient_summary = next((s for s in summaries if s.player_id == suggestion.recipient_id), None)
            result["recipient_owed_money"] = recipient_summary and recipient_summary.balance > Decimal("0.01")

            validation_results.append(result)

        return validation_results

    @staticmethod
    def generate_random_payment_scenario(
        game_setup: TestGameSetup,
        num_payments: int = 20,
        seed: int = 42
    ) -> List[Tuple[str, str, Decimal, str]]:
        """
        Generate a random but valid payment scenario.

        Args:
            game_setup: Game setup data
            num_payments: Number of payments to generate
            seed: Random seed for reproducibility

        Returns:
            List of payment tuples
        """
        import random
        random.seed(seed)

        payments = []
        player_ids = game_setup.player_ids

        for i in range(num_payments):
            # Pick random payer and recipient
            payer_idx = random.randint(0, len(player_ids) - 1)
            recipient_idx = random.randint(0, len(player_ids) - 1)

            # Ensure different players
            while recipient_idx == payer_idx:
                recipient_idx = random.randint(0, len(player_ids) - 1)

            # Random amount between $0.01 and $100.00
            amount_cents = random.randint(1, 10000)
            amount = Decimal(amount_cents) / 100

            payments.append((
                player_ids[payer_idx],
                player_ids[recipient_idx],
                amount,
                f"Random_{i}"
            ))

        return payments

    @staticmethod
    def simulate_settlement_execution(game_id: str, max_iterations: int = 10) -> Dict[str, Any]:
        """
        Simulate complete settlement execution and return metrics.

        Returns:
            Dictionary with settlement execution metrics
        """
        with SessionLocal() as db_session:
            payment_service = PaymentService(db_session)
            payment_date = datetime.now(timezone.utc)

            initial_snapshot = FinancialIntegrityTestUtils.take_financial_snapshot(game_id)
            iterations = 0
            total_suggestions = 0
            total_settlement_amount = Decimal("0")

            while iterations < max_iterations:
                suggestions = payment_service.get_settlement_suggestions(game_id)

                if not suggestions:
                    break

                # Execute all suggestions
                for idx, suggestion in enumerate(suggestions):
                    from uuid import uuid4
                    unique_id = str(uuid4())[:8]
                    payment_service.record_payment(
                        game_id=game_id,
                        payer_id=suggestion.payer_id,
                        recipient_id=suggestion.recipient_id,
                        amount=suggestion.amount,
                        payment_date=payment_date,
                        payment_method="Settlement",
                        reference_id=f"settlement_{iterations}_{idx}_{unique_id}",
                        created_by="test"
                    )
                    total_settlement_amount += suggestion.amount

                total_suggestions += len(suggestions)
                iterations += 1

            db_session.commit()
            final_snapshot = FinancialIntegrityTestUtils.take_financial_snapshot(game_id)

        return {
            "iterations": iterations,
            "total_suggestions": total_suggestions,
            "total_settlement_amount": total_settlement_amount,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "settlement_completed": abs(final_snapshot.total_balances) < Decimal("0.01")
        }

    @staticmethod
    def create_complex_debt_web(game_setup: TestGameSetup) -> List[Tuple[str, str, Decimal, str]]:
        """
        Create a complex debt web that tests settlement optimization.

        Returns:
            List of payments that create circular debts
        """
        player_ids = game_setup.player_ids

        if len(player_ids) < 3:
            raise ValueError("Need at least 3 players for complex debt web")

        payments = []

        # Create circular debt: A pays B, B pays C, C pays A
        payments.extend([
            (player_ids[0], player_ids[1], Decimal("50.00"), "CircularA->B"),
            (player_ids[1], player_ids[2], Decimal("30.00"), "CircularB->C"),
            (player_ids[2], player_ids[0], Decimal("20.00"), "CircularC->A"),
        ])

        # Add more complexity if we have more players
        if len(player_ids) >= 4:
            payments.extend([
                (player_ids[0], player_ids[3], Decimal("25.00"), "ComplexA->D"),
                (player_ids[3], player_ids[1], Decimal("15.00"), "ComplexD->B"),
            ])

        if len(player_ids) >= 5:
            payments.extend([
                (player_ids[4], player_ids[0], Decimal("40.00"), "ComplexE->A"),
                (player_ids[2], player_ids[4], Decimal("35.00"), "ComplexC->E"),
            ])

        return payments


# Performance testing utilities
class PerformanceTestUtils:
    """Utilities for performance testing of financial operations."""

    @staticmethod
    def time_operation(operation_func, *args, **kwargs) -> Tuple[Any, float]:
        """
        Time an operation and return result and duration.

        Returns:
            Tuple of (result, duration_in_seconds)
        """
        import time
        start_time = time.time()
        result = operation_func(*args, **kwargs)
        duration = time.time() - start_time
        return result, duration

    @staticmethod
    def benchmark_payment_operations(game_id: str, num_operations: int = 100) -> Dict[str, float]:
        """
        Benchmark various payment operations.

        Returns:
            Dictionary with operation timings
        """
        with SessionLocal() as db_session:
            payment_service = PaymentService(db_session)

            # Benchmark payment summary
            _, summary_time = PerformanceTestUtils.time_operation(
                payment_service.get_payment_summary, game_id
            )

            # Benchmark settlement suggestions
            _, settlement_time = PerformanceTestUtils.time_operation(
                payment_service.get_settlement_suggestions, game_id
            )

            # Benchmark payment history
            _, history_time = PerformanceTestUtils.time_operation(
                payment_service.get_payment_history, game_id, limit=num_operations
            )

        return {
            "payment_summary_time": summary_time,
            "settlement_suggestions_time": settlement_time,
            "payment_history_time": history_time
        }


# Data validation utilities
class ValidationUtils:
    """Utilities for validating financial data integrity."""

    @staticmethod
    def validate_player_balance_consistency(game_id: str) -> List[str]:
        """
        Validate that stored balances match calculated balances.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        with SessionLocal() as db:
            payment_service = PaymentService(db)
            summaries = payment_service.get_payment_summary(game_id)
            for summary in summaries:
                player_id = summary.player_id

                # Manually calculate poker winnings
                poker_winnings = db.execute(text("""
                    SELECT COALESCE(SUM(sps.net), 0) as total_winnings
                    FROM session_player_summaries sps
                    JOIN sessions s ON sps.session_id = s.id
                    WHERE s.game_id = :game_id AND sps.player_id = :player_id
                """), {"game_id": game_id, "player_id": player_id}).scalar() or 0

                # Manually calculate payments
                total_paid = db.execute(text("""
                    SELECT COALESCE(SUM(amount_cents), 0) as total_paid
                    FROM payment_transactions
                    WHERE game_id = :game_id AND payer_id = :player_id AND status = 'completed'
                """), {"game_id": game_id, "player_id": player_id}).scalar() or 0

                total_received = db.execute(text("""
                    SELECT COALESCE(SUM(amount_cents), 0) as total_received
                    FROM payment_transactions
                    WHERE game_id = :game_id AND recipient_id = :player_id AND status = 'completed'
                """), {"game_id": game_id, "player_id": player_id}).scalar() or 0

                # Convert to decimals and compare
                calc_poker = Decimal(poker_winnings) / 100
                calc_paid = Decimal(total_paid) / 100
                calc_received = Decimal(total_received) / 100
                calc_balance = calc_received - calc_poker

                # Check for discrepancies
                if summary.poker_net_winnings != calc_poker:
                    errors.append(f"Player {player_id}: poker winnings mismatch (stored: {summary.poker_net_winnings}, calculated: {calc_poker})")

                if summary.total_paid != calc_paid:
                    errors.append(f"Player {player_id}: total paid mismatch (stored: {summary.total_paid}, calculated: {calc_paid})")

                if summary.total_received != calc_received:
                    errors.append(f"Player {player_id}: total received mismatch (stored: {summary.total_received}, calculated: {calc_received})")

                if summary.balance != calc_balance:
                    errors.append(f"Player {player_id}: balance mismatch (stored: {summary.balance}, calculated: {calc_balance})")

        return errors