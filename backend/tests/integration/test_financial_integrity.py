"""
Critical Financial Integrity Tests - Zero-Sum Validation

These tests prevent the most catastrophic financial errors:
- Money creation (total paid ≠ total received)
- Money destruction (balances don't add up to zero)
- Precision loss (floating point errors)
- Calculation errors in balance reconstruction

THESE ARE THE MOST IMPORTANT TESTS - THEY VERIFY THE CORE FINANCIAL INVARIANTS.
"""

import pytest
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import text
import random

from src.db.database import SessionLocal, engine
from src.db.models import Game, Player, PaymentTransaction, PaymentBalance, Session, SessionPlayerSummary
from src.services.payment_service_v2 import PaymentService


class TestFinancialIntegrity:
    """Critical tests that verify fundamental financial invariants."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clean database before and after each test with force cleanup."""
        # Force cleanup with CASCADE to handle any dangling references
        with engine.connect() as conn:
            # Use CASCADE to handle any foreign key dependencies
            conn.execute(text("DELETE FROM payment_transactions CASCADE"))
            conn.execute(text("DELETE FROM payment_balances CASCADE"))
            conn.execute(text("DELETE FROM session_player_summaries CASCADE"))
            conn.execute(text("DELETE FROM sessions CASCADE"))
            conn.execute(text("DELETE FROM game_players CASCADE"))
            conn.execute(text("DELETE FROM players CASCADE"))
            conn.execute(text("DELETE FROM games CASCADE"))
            # Also clear any audit logs that might be interfering
            conn.execute(text("DELETE FROM audit_log CASCADE"))
            conn.commit()

        yield

        # Clean up after test with same force cleanup
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM payment_transactions CASCADE"))
            conn.execute(text("DELETE FROM payment_balances CASCADE"))
            conn.execute(text("DELETE FROM session_player_summaries CASCADE"))
            conn.execute(text("DELETE FROM sessions CASCADE"))
            conn.execute(text("DELETE FROM game_players CASCADE"))
            conn.execute(text("DELETE FROM players CASCADE"))
            conn.execute(text("DELETE FROM games CASCADE"))
            conn.execute(text("DELETE FROM audit_log CASCADE"))
            conn.commit()

    def create_test_game_with_players(self, num_players=3, poker_results=None):
        """Create a test game with players and session data."""
        if poker_results is None:
            # Default balanced poker results (sum = 0)
            poker_results = [5000, -2000, -3000]

        # Ensure poker results sum to zero (critical financial invariant)
        assert sum(poker_results) == 0, f"Poker results must sum to 0, got {sum(poker_results)}"

        with SessionLocal() as db:
            # Create game
            game = Game(
                public_code=f"TEST{uuid4().hex[:6].upper()}",
                admin_code=f"admin-{uuid4()}",
                title="Financial Integrity Test Game"
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

    def verify_zero_sum_invariant(self, summaries):
        """
        CRITICAL: Verify that all balances sum to zero.
        This is the fundamental financial invariant.
        """
        total_poker_winnings = sum(s.poker_net_winnings for s in summaries)
        total_paid = sum(s.total_paid for s in summaries)
        total_received = sum(s.total_received for s in summaries)
        total_balances = sum(s.balance for s in summaries)

        # Core financial invariants
        assert total_paid == total_received, \
            f"Money creation/destruction: paid=${total_paid}, received=${total_received}"

        assert total_poker_winnings == Decimal("0"), \
            f"Poker results not zero-sum: total=${total_poker_winnings}"

        # The correct zero-sum invariant is based on net balances for settlements
        # Calculate net balance as the service does: (poker_winnings + paid) - received
        net_balances_sum = sum((s.poker_net_winnings + s.total_paid) - s.total_received for s in summaries)
        assert abs(net_balances_sum) < Decimal("0.01"), \
            f"Net balances don't sum to zero: total=${net_balances_sum}"

    def verify_balance_reconstruction(self, game_id, summaries):
        """
        CRITICAL: Verify balances can be reconstructed from payment history.
        Stored balances must match calculated balances.
        """
        with SessionLocal() as db:
            # Manually recalculate all balances from scratch
            for summary in summaries:
                player_id = summary.player_id

                # Get poker winnings from sessions
                poker_winnings = db.execute(text("""
                    SELECT COALESCE(SUM(sps.net), 0) as total_winnings
                    FROM session_player_summaries sps
                    JOIN sessions s ON sps.session_id = s.id
                    WHERE s.game_id = :game_id AND sps.player_id = :player_id
                """), {"game_id": game_id, "player_id": player_id}).scalar() or 0

                # Get total paid
                total_paid = db.execute(text("""
                    SELECT COALESCE(SUM(amount_cents), 0) as total_paid
                    FROM payment_transactions
                    WHERE game_id = :game_id AND payer_id = :player_id AND status = 'completed'
                """), {"game_id": game_id, "player_id": player_id}).scalar() or 0

                # Get total received
                total_received = db.execute(text("""
                    SELECT COALESCE(SUM(amount_cents), 0) as total_received
                    FROM payment_transactions
                    WHERE game_id = :game_id AND recipient_id = :player_id AND status = 'completed'
                """), {"game_id": game_id, "player_id": player_id}).scalar() or 0

                # Convert to decimals
                calculated_poker_winnings = Decimal(poker_winnings) / 100
                calculated_paid = Decimal(total_paid) / 100
                calculated_received = Decimal(total_received) / 100
                calculated_balance = calculated_poker_winnings + calculated_paid - calculated_received

                # Verify stored values match calculated values
                assert summary.poker_net_winnings == calculated_poker_winnings, \
                    f"Player {player_id}: stored poker winnings ${summary.poker_net_winnings} != calculated ${calculated_poker_winnings}"

                assert summary.total_paid == calculated_paid, \
                    f"Player {player_id}: stored paid ${summary.total_paid} != calculated ${calculated_paid}"

                assert summary.total_received == calculated_received, \
                    f"Player {player_id}: stored received ${summary.total_received} != calculated ${calculated_received}"

                assert summary.balance == calculated_balance, \
                    f"Player {player_id}: stored balance ${summary.balance} != calculated ${calculated_balance}"

    def test_zero_sum_invariant_simple_payments(self, db_session):
        """
        CRITICAL: Game balances must always sum to zero after any payments.
        """
        game_id, player_ids = self.create_test_game_with_players(3)
        alice_id, bob_id, charlie_id = player_ids
        payment_service = PaymentService(db_session)

        payment_date = datetime.now(timezone.utc)

        # Make various payments
        payment_service.record_payment(game_id, alice_id, bob_id, Decimal("25.00"), payment_date, "Test", created_by="test")
        payment_service.record_payment(game_id, bob_id, charlie_id, Decimal("15.00"), payment_date, "Test", created_by="test")
        payment_service.record_payment(game_id, charlie_id, alice_id, Decimal("10.00"), payment_date, "Test", created_by="test")

        # Commit so verification queries can see the data
        db_session.commit()

        # Verify invariants
        summaries = payment_service.get_payment_summary(game_id)
        self.verify_zero_sum_invariant(summaries)
        self.verify_balance_reconstruction(game_id, summaries)

    def test_zero_sum_invariant_complex_scenario(self, db_session):
        """
        CRITICAL: Zero-sum must hold for complex payment scenarios.
        """
        game_id, player_ids = self.create_test_game_with_players(5,
            poker_results=[10000, 5000, -3000, -7000, -5000])  # Larger, more complex game
        payment_service = PaymentService(db_session)

        payment_date = datetime.now(timezone.utc)

        # Complex payment patterns
        payments = [
            (player_ids[0], player_ids[1], Decimal("75.50")),  # Alice -> Bob
            (player_ids[1], player_ids[2], Decimal("30.25")),  # Bob -> Charlie
            (player_ids[2], player_ids[3], Decimal("45.75")),  # Charlie -> David
            (player_ids[3], player_ids[4], Decimal("20.00")),  # David -> Eve
            (player_ids[4], player_ids[0], Decimal("15.50")),  # Eve -> Alice
            (player_ids[0], player_ids[3], Decimal("35.00")),  # Alice -> David
            (player_ids[2], player_ids[1], Decimal("12.25")),  # Charlie -> Bob
        ]

        # Execute all payments
        for payer_id, recipient_id, amount in payments:
            payment_service.record_payment(
                game_id, payer_id, recipient_id, amount, payment_date, "Complex", created_by="test"
            )

        # Commit so verification queries can see the data
        db_session.commit()

        # Verify invariants after each payment
        summaries = payment_service.get_payment_summary(game_id)
        self.verify_zero_sum_invariant(summaries)
        self.verify_balance_reconstruction(game_id, summaries)

    def test_precision_preservation_edge_cases(self, db_session):
        """
        CRITICAL: Decimal precision must be preserved in all edge cases.
        No floating-point errors that could create/destroy money.
        """
        game_id, player_ids = self.create_test_game_with_players(2, poker_results=[3000, -3000])
        alice_id, bob_id = player_ids
        payment_service = PaymentService(db_session)

        payment_date = datetime.now(timezone.utc)

        # Test problematic amounts that cause floating-point issues
        problematic_amounts = [
            Decimal("0.01"),      # Single cent
            Decimal("10.03"),     # Classic floating-point problem
            Decimal("999.99"),    # Large amount with cents
            Decimal("1.11"),      # Repeating decimals
            Decimal("3.33"),      # More repeating decimals
            Decimal("0.07"),      # Another problematic amount
            Decimal("1234.56"),   # Random precise amount
        ]

        total_sent = Decimal("0")
        for amount in problematic_amounts:
            payment_service.record_payment(
                game_id, alice_id, bob_id, amount, payment_date, "Precision", created_by="test"
            )
            total_sent += amount

        # Commit so verification queries can see the data
        db_session.commit()

        # Verify exact precision
        summaries = payment_service.get_payment_summary(game_id)
        alice_summary = next(s for s in summaries if s.player_id == alice_id)
        bob_summary = next(s for s in summaries if s.player_id == bob_id)

        assert alice_summary.total_paid == total_sent, \
            f"Precision lost: expected ${total_sent}, got ${alice_summary.total_paid}"

        assert bob_summary.total_received == total_sent, \
            f"Precision lost: expected ${total_sent}, got ${bob_summary.total_received}"

        # Verify zero-sum with exact precision
        self.verify_zero_sum_invariant(summaries)

    def test_money_conservation_in_settlements(self, db_session):
        """
        CRITICAL: Settlement suggestions must conserve money perfectly.
        Total debt before settlements = total of suggested payments.
        """
        game_id, player_ids = self.create_test_game_with_players(4,
            poker_results=[15000, 5000, -8000, -12000])  # Complex debt scenario
        payment_service = PaymentService(db_session)

        # Get initial summary before any payments
        initial_summaries = payment_service.get_payment_summary(game_id)

        # Calculate total debt owed in the system
        total_debt_owed = sum(max(Decimal("0"), -s.balance) for s in initial_summaries)
        total_credit_due = sum(max(Decimal("0"), s.balance) for s in initial_summaries)

        # These should be equal (debt owed = credit due)
        assert total_debt_owed == total_credit_due, \
            f"Initial state not balanced: debt=${total_debt_owed}, credit=${total_credit_due}"

        # Get settlement suggestions
        suggestions = payment_service.get_settlement_suggestions(game_id)

        # Calculate total suggested payments
        total_suggested = sum(s.amount for s in suggestions)

        # Total suggested payments should equal total debt
        assert total_suggested == total_debt_owed, \
            f"Settlement suggestions don't match debt: suggested=${total_suggested}, debt=${total_debt_owed}"

        # Verify settlements would actually achieve zero balances
        # Simulate executing all suggestions
        payment_date = datetime.now(timezone.utc)
        for suggestion in suggestions:
            payment_service.record_payment(
                game_id, suggestion.payer_id, suggestion.recipient_id,
                suggestion.amount, payment_date, "Settlement", created_by="test"
            )

        # Commit so verification queries can see the data
        db_session.commit()

        # After settlements, all net balances (for settlement purposes) should be near zero
        final_summaries = payment_service.get_payment_summary(game_id)
        for summary in final_summaries:
            net_balance = (summary.poker_net_winnings + summary.total_paid) - summary.total_received
            assert abs(net_balance) < Decimal("0.01"), \
                f"Player {summary.player_name} net balance not settled: ${net_balance}"

        # Verify overall financial integrity
        self.verify_zero_sum_invariant(final_summaries)

    def test_invariant_preservation_across_operations(self, db_session):
        """
        CRITICAL: Financial invariants must hold after every single operation.
        Property-based testing approach.
        """
        game_id, player_ids = self.create_test_game_with_players(4, poker_results=[8000, 2000, -5000, -5000])
        payment_service = PaymentService(db_session)

        payment_date = datetime.now(timezone.utc)

        # Generate random payment operations
        random.seed(42)  # Deterministic for reproducibility
        operations = []

        for _ in range(50):  # 50 random operations
            payer_idx = random.randint(0, len(player_ids) - 1)
            recipient_idx = random.randint(0, len(player_ids) - 1)

            # Ensure different players
            while recipient_idx == payer_idx:
                recipient_idx = random.randint(0, len(player_ids) - 1)

            # Random amount between $0.01 and $100.00
            amount_cents = random.randint(1, 10000)
            amount = Decimal(amount_cents) / 100

            operations.append((payer_idx, recipient_idx, amount))

        # Execute operations and verify invariants after each
        for i, (payer_idx, recipient_idx, amount) in enumerate(operations):
            try:
                payment_service.record_payment(
                    game_id, player_ids[payer_idx], player_ids[recipient_idx],
                    amount, payment_date, f"Random_{i}", created_by="test"
                )

                # Commit so verification queries can see the data
                db_session.commit()

                # Verify invariants after EVERY operation
                summaries = payment_service.get_payment_summary(game_id)
                self.verify_zero_sum_invariant(summaries)

            except Exception as e:
                # If operation fails, verify state is still consistent
                summaries = payment_service.get_payment_summary(game_id)
                self.verify_zero_sum_invariant(summaries)
                # Re-raise the exception for investigation
                raise e

        # Final comprehensive verification
        final_summaries = payment_service.get_payment_summary(game_id)
        self.verify_zero_sum_invariant(final_summaries)
        self.verify_balance_reconstruction(game_id, final_summaries)

    def test_cent_precision_edge_cases(self, db_session):
        """
        CRITICAL: Verify cent precision is never lost in any calculation.
        Tests the most problematic precision scenarios.
        """
        game_id, player_ids = self.create_test_game_with_players(3)
        alice_id, bob_id, charlie_id = player_ids
        payment_service = PaymentService(db_session)

        payment_date = datetime.now(timezone.utc)

        # Test cases that commonly cause precision issues
        test_cases = [
            # Amount, Expected cents storage
            (Decimal("0.01"), 1),
            (Decimal("0.99"), 99),
            (Decimal("1.00"), 100),
            (Decimal("10.03"), 1003),  # Classic problem case
            (Decimal("999.99"), 99999),
            (Decimal("1000.00"), 100000),
        ]

        for amount, expected_cents in test_cases:
            payment_service.record_payment(
                game_id, alice_id, bob_id, amount, payment_date, "Precision", created_by="test"
            )

            # Commit so verification queries can see the data
            db_session.commit()

            # Verify storage precision by checking database directly
            with SessionLocal() as db:
                last_payment = db.query(PaymentTransaction).filter(
                    PaymentTransaction.game_id == game_id,
                    PaymentTransaction.payer_id == alice_id,
                    PaymentTransaction.recipient_id == bob_id
                ).order_by(PaymentTransaction.created_at.desc()).first()

                assert last_payment.amount_cents == expected_cents, \
                    f"Amount ${amount} stored as {last_payment.amount_cents} cents, expected {expected_cents}"

                # Verify retrieval precision
                retrieved_amount = last_payment.amount
                assert retrieved_amount == amount, \
                    f"Retrieved amount ${retrieved_amount} != original ${amount}"

        # Verify overall precision in summaries
        summaries = payment_service.get_payment_summary(game_id)
        self.verify_zero_sum_invariant(summaries)

    def test_large_scale_financial_integrity(self, db_session):
        """
        CRITICAL: Financial integrity must hold even with large amounts and many players.
        Stress test for precision and invariant preservation.
        """
        # Create larger game with more players
        num_players = 10
        large_poker_results = [50000, 25000, 15000, 10000, 5000,
                              -15000, -20000, -25000, -30000, -15000]  # Sums to 0
        assert sum(large_poker_results) == 0

        game_id, player_ids = self.create_test_game_with_players(num_players, large_poker_results)
        payment_service = PaymentService(db_session)

        payment_date = datetime.now(timezone.utc)

        # Create large payments
        large_amounts = [
            Decimal("1500.75"),
            Decimal("2250.50"),
            Decimal("999.99"),
            Decimal("3333.33"),
            Decimal("777.77"),
        ]

        payment_count = 0
        for i, amount in enumerate(large_amounts):
            payer_id = player_ids[i % len(player_ids)]
            recipient_id = player_ids[(i + 1) % len(player_ids)]

            payment_service.record_payment(
                game_id, payer_id, recipient_id, amount, payment_date, "Large", created_by="test"
            )
            payment_count += 1

            # Commit so verification queries can see the data
            db_session.commit()

            # Verify invariants after each large payment
            summaries = payment_service.get_payment_summary(game_id)
            self.verify_zero_sum_invariant(summaries)

        # Verify final state
        final_summaries = payment_service.get_payment_summary(game_id)
        self.verify_zero_sum_invariant(final_summaries)
        self.verify_balance_reconstruction(game_id, final_summaries)

        # Verify total amounts match expectations
        total_payments_made = sum(large_amounts)
        total_paid_summary = sum(s.total_paid for s in final_summaries)
        total_received_summary = sum(s.total_received for s in final_summaries)

        assert total_paid_summary == total_payments_made
        assert total_received_summary == total_payments_made
        assert total_paid_summary == total_received_summary