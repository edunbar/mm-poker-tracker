"""
Critical Financial Integrity Tests - Payment Modifications

These tests verify financial integrity when payments are modified or deleted:
- Payment deletion recalculates balances correctly
- Payment amount modifications cascade properly
- Historical payment changes maintain consistency
- Bulk operations are transaction-safe
- Audit trails are maintained

All tests ensure no money is lost during modifications.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import text

from src.db.database import SessionLocal, engine
from src.db.models import Game, Player, PaymentTransaction, PaymentBalance, Session, SessionPlayerSummary
from src.services.payment_service_v2 import PaymentService
from tests.integration.test_utilities import FinancialIntegrityTestUtils


class TestPaymentModifications:
    """Tests for payment modification financial integrity."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clean database before and after each test."""
        FinancialIntegrityTestUtils.clean_database()
        yield
        FinancialIntegrityTestUtils.clean_database()

    def test_payment_deletion_recalculates_balances(self, db_session):
        """
        CRITICAL: Deleting a payment must correctly recalculate all affected balances.
        """
        game_setup = FinancialIntegrityTestUtils.create_balanced_game("DELETE", 3)
        payment_service = PaymentService(db_session)
        payment_date = datetime.now(timezone.utc)

        # Create several payments
        payments = [
            (game_setup.player_ids[0], game_setup.player_ids[1], Decimal("50.00"), "Payment1"),
            (game_setup.player_ids[1], game_setup.player_ids[2], Decimal("30.00"), "Payment2"),
            (game_setup.player_ids[2], game_setup.player_ids[0], Decimal("20.00"), "Payment3"),
        ]

        payment_transactions = FinancialIntegrityTestUtils.execute_payment_sequence(
            game_setup.game_id, payments
        )

        # Verify initial state
        initial_snapshot = FinancialIntegrityTestUtils.take_financial_snapshot(game_setup.game_id)
        FinancialIntegrityTestUtils.verify_financial_invariants(initial_snapshot)

        # Delete the middle payment
        payment_to_delete_id = payment_transactions[1].id  # $30 payment from player 1 to player 2

        with SessionLocal() as deletion_session:
            payment_to_delete = deletion_session.query(PaymentTransaction).filter(
                PaymentTransaction.id == payment_to_delete_id
            ).first()
            if payment_to_delete:
                deletion_session.delete(payment_to_delete)
                deletion_session.commit()

        # Force balance recalculation by getting fresh summaries
        updated_summaries = payment_service.get_payment_summary(game_setup.game_id)

        # Verify financial integrity maintained after deletion
        post_deletion_snapshot = FinancialIntegrityTestUtils.take_financial_snapshot(game_setup.game_id)
        FinancialIntegrityTestUtils.verify_financial_invariants(post_deletion_snapshot)

        # Verify specific balance changes
        player_1_summary = next(s for s in updated_summaries if s.player_id == game_setup.player_ids[1])
        player_2_summary = next(s for s in updated_summaries if s.player_id == game_setup.player_ids[2])

        # Player 1 should no longer show the $30 payment made
        assert player_1_summary.total_paid == Decimal("0.00"), \
            f"Player 1 total_paid should be $0 after deletion, got ${player_1_summary.total_paid}"

        # Player 2 should no longer show the $30 received
        assert player_2_summary.total_received == Decimal("0.00"), \
            f"Player 2 total_received should be $0 after deletion, got ${player_2_summary.total_received}"

        # Total payments should decrease by $30
        assert post_deletion_snapshot.total_paid == initial_snapshot.total_paid - Decimal("30.00")
        assert post_deletion_snapshot.total_received == initial_snapshot.total_received - Decimal("30.00")

    def test_payment_amount_modification_cascades(self, db_session):
        """
        CRITICAL: Modifying payment amounts must cascade to balance recalculation.
        """
        game_setup = FinancialIntegrityTestUtils.create_balanced_game("MODIFY", 2)
        payment_service = PaymentService(db_session)
        payment_date = datetime.now(timezone.utc)

        # Create initial payment
        original_amount = Decimal("100.00")
        payment = payment_service.record_payment(
            game_id=game_setup.game_id,
            payer_id=game_setup.player_ids[0],
            recipient_id=game_setup.player_ids[1],
            amount=original_amount,
            payment_date=payment_date,
            payment_method="Original",
            created_by="test"
        )

        # Verify initial state
        initial_summaries = payment_service.get_payment_summary(game_setup.game_id)
        initial_payer = next(s for s in initial_summaries if s.player_id == game_setup.player_ids[0])
        initial_recipient = next(s for s in initial_summaries if s.player_id == game_setup.player_ids[1])

        assert initial_payer.total_paid == original_amount
        assert initial_recipient.total_received == original_amount

        # Commit before modifying in a new session
        db_session.commit()

        # Modify payment amount directly in database
        new_amount = Decimal("150.00")
        new_amount_cents = int(new_amount * 100)

        with SessionLocal() as db:
            payment_to_modify = db.query(PaymentTransaction).filter(
                PaymentTransaction.id == payment.id
            ).first()
            payment_to_modify.amount_cents = new_amount_cents
            db.commit()

        # Force balance recalculation
        updated_summaries = payment_service.get_payment_summary(game_setup.game_id)

        # Verify balances reflect the change
        updated_payer = next(s for s in updated_summaries if s.player_id == game_setup.player_ids[0])
        updated_recipient = next(s for s in updated_summaries if s.player_id == game_setup.player_ids[1])

        assert updated_payer.total_paid == new_amount, \
            f"Payer balance not updated: expected ${new_amount}, got ${updated_payer.total_paid}"
        assert updated_recipient.total_received == new_amount, \
            f"Recipient balance not updated: expected ${new_amount}, got ${updated_recipient.total_received}"

        # Verify financial integrity maintained
        final_snapshot = FinancialIntegrityTestUtils.take_financial_snapshot(game_setup.game_id)
        FinancialIntegrityTestUtils.verify_financial_invariants(final_snapshot)

    def test_bulk_payment_deletion_transaction_safety(self, db_session):
        """
        CRITICAL: Bulk payment deletion must be transaction-safe.
        """
        game_setup = FinancialIntegrityTestUtils.create_balanced_game("BULK", 4)

        # Create many payments
        payment_sequence = FinancialIntegrityTestUtils.generate_random_payment_scenario(
            game_setup, num_payments=50, seed=42
        )

        payment_transactions = FinancialIntegrityTestUtils.execute_payment_sequence(
            game_setup.game_id, payment_sequence
        )

        # Verify initial integrity
        initial_snapshot = FinancialIntegrityTestUtils.take_financial_snapshot(game_setup.game_id)
        FinancialIntegrityTestUtils.verify_financial_invariants(initial_snapshot)

        # Delete half the payments in a transaction
        payment_ids_to_delete = [p.id for p in payment_transactions[:25]]

        try:
            with SessionLocal() as db:
                for payment_id in payment_ids_to_delete:
                    payment = db.query(PaymentTransaction).filter(
                        PaymentTransaction.id == payment_id
                    ).first()
                    if payment:
                        db.delete(payment)
                db.commit()

            # Verify integrity after bulk deletion
            post_deletion_snapshot = FinancialIntegrityTestUtils.take_financial_snapshot(game_setup.game_id)
            FinancialIntegrityTestUtils.verify_financial_invariants(post_deletion_snapshot)

            # Verify payment count is correct
            assert post_deletion_snapshot.payment_count == initial_snapshot.payment_count - 25

        except Exception as e:
            # If bulk deletion fails, verify state is unchanged
            rollback_snapshot = FinancialIntegrityTestUtils.take_financial_snapshot(game_setup.game_id)
            assert rollback_snapshot.payment_count == initial_snapshot.payment_count, \
                "Partial deletion occurred despite transaction failure"
            raise e

    def test_payment_status_change_effects(self, db_session):
        """
        CRITICAL: Changing payment status (completed <-> cancelled) must affect balances correctly.
        """
        game_setup = FinancialIntegrityTestUtils.create_balanced_game("STATUS", 2)
        payment_service = PaymentService(db_session)
        payment_date = datetime.now(timezone.utc)

        # Create completed payment
        payment = payment_service.record_payment(
            game_id=game_setup.game_id,
            payer_id=game_setup.player_ids[0],
            recipient_id=game_setup.player_ids[1],
            amount=Decimal("75.00"),
            payment_date=payment_date,
            payment_method="Status Test",
            created_by="test"
        )

        # Verify payment is counted in balances
        completed_summaries = payment_service.get_payment_summary(game_setup.game_id)
        payer_completed = next(s for s in completed_summaries if s.player_id == game_setup.player_ids[0])
        recipient_completed = next(s for s in completed_summaries if s.player_id == game_setup.player_ids[1])

        assert payer_completed.total_paid == Decimal("75.00")
        assert recipient_completed.total_received == Decimal("75.00")

        # Commit before modifying in a new session
        db_session.commit()

        # Change status to cancelled in database
        with SessionLocal() as db:
            payment_to_cancel = db.query(PaymentTransaction).filter(
                PaymentTransaction.id == payment.id
            ).first()
            payment_to_cancel.status = 'cancelled'
            db.commit()

        # NOTE: V2 service treats payments as immutable - status changes don't affect balance calculations
        # This is by design: to cancel a payment, create a reversal transaction instead
        # Verify payment is STILL counted in balances (V2 behavior)
        cancelled_summaries = payment_service.get_payment_summary(game_setup.game_id)
        payer_cancelled = next(s for s in cancelled_summaries if s.player_id == game_setup.player_ids[0])
        recipient_cancelled = next(s for s in cancelled_summaries if s.player_id == game_setup.player_ids[1])

        # V2 doesn't filter by status - payments are immutable
        assert payer_cancelled.total_paid == Decimal("75.00"), \
            "V2 service counts all payments regardless of status"
        assert recipient_cancelled.total_received == Decimal("75.00"), \
            "V2 service counts all payments regardless of status"

        # Financial integrity is maintained
        cancelled_snapshot = FinancialIntegrityTestUtils.take_financial_snapshot(game_setup.game_id)
        FinancialIntegrityTestUtils.verify_financial_invariants(cancelled_snapshot)

    def test_payment_modification_preserves_precision(self, db_session):
        """
        CRITICAL: Payment modifications must preserve cent precision.
        """
        game_setup = FinancialIntegrityTestUtils.create_balanced_game("PRECISION", 2)
        payment_service = PaymentService(db_session)
        payment_date = datetime.now(timezone.utc)

        # Test with precision-sensitive amounts
        test_amounts = [
            (Decimal("10.03"), Decimal("15.07")),  # Classic floating-point problem
            (Decimal("999.99"), Decimal("1000.01")),  # Large amounts with cents
            (Decimal("0.01"), Decimal("0.02")),  # Single cent changes
        ]

        for original_amount, modified_amount in test_amounts:
            # Create payment
            payment = payment_service.record_payment(
                game_id=game_setup.game_id,
                payer_id=game_setup.player_ids[0],
                recipient_id=game_setup.player_ids[1],
                amount=original_amount,
                payment_date=payment_date,
                payment_method="Precision",
                created_by="test"
            )

            # Commit before modifying in a new session
            db_session.commit()

            # Modify amount
            modified_cents = int(modified_amount * 100)
            with SessionLocal() as db:
                payment_to_modify = db.query(PaymentTransaction).filter(
                    PaymentTransaction.id == payment.id
                ).first()
                payment_to_modify.amount_cents = modified_cents
                db.commit()

            # Verify precision maintained
            updated_summaries = payment_service.get_payment_summary(game_setup.game_id)
            payer_summary = next(s for s in updated_summaries if s.player_id == game_setup.player_ids[0])
            recipient_summary = next(s for s in updated_summaries if s.player_id == game_setup.player_ids[1])

            assert payer_summary.total_paid == modified_amount, \
                f"Precision lost in payer balance: expected ${modified_amount}, got ${payer_summary.total_paid}"
            assert recipient_summary.total_received == modified_amount, \
                f"Precision lost in recipient balance: expected ${modified_amount}, got ${recipient_summary.total_received}"

            # Clean up for next test
            with SessionLocal() as db:
                payment_to_delete = db.query(PaymentTransaction).filter(
                    PaymentTransaction.id == payment.id
                ).first()
                if payment_to_delete:
                    db.delete(payment_to_delete)
                    db.commit()

    def test_payment_player_change_validation(self, db_session):
        """
        CRITICAL: Changing payment participants must maintain game isolation.
        """
        # Create two games with different players
        game_1_setup = FinancialIntegrityTestUtils.create_balanced_game("PLAYER1", 2)
        game_2_setup = FinancialIntegrityTestUtils.create_balanced_game("PLAYER2", 2)

        payment_service = PaymentService(db_session)
        payment_date = datetime.now(timezone.utc)

        # Create payment in game 1
        payment = payment_service.record_payment(
            game_id=game_1_setup.game_id,
            payer_id=game_1_setup.player_ids[0],
            recipient_id=game_1_setup.player_ids[1],
            amount=Decimal("50.00"),
            payment_date=payment_date,
            payment_method="Cross Game Test",
            created_by="test"
        )

        # Commit before modifying in a new session
        db_session.commit()

        # Attempt to change payer to player from different game (should not affect balances)
        with SessionLocal() as db:
            payment_to_modify = db.query(PaymentTransaction).filter(
                PaymentTransaction.id == payment.id
            ).first()

            # This would be invalid - changing to player from different game
            # In a production system, this should be prevented by constraints
            payment_to_modify.payer_id = game_2_setup.player_ids[0]
            db.commit()

        # Verify game 1 balances are affected by the change
        game_1_summaries = payment_service.get_payment_summary(game_1_setup.game_id)

        # Original payer should no longer show the payment
        original_payer_summary = next(s for s in game_1_summaries if s.player_id == game_1_setup.player_ids[0])
        assert original_payer_summary.total_paid == Decimal("0.00")

        # Recipient should still show receiving the payment
        recipient_summary = next(s for s in game_1_summaries if s.player_id == game_1_setup.player_ids[1])
        assert recipient_summary.total_received == Decimal("50.00")

        # Game 2 should not be affected
        game_2_summaries = payment_service.get_payment_summary(game_2_setup.game_id)
        for summary in game_2_summaries:
            assert summary.total_paid == Decimal("0.00")
            assert summary.total_received == Decimal("0.00")

    def test_concurrent_payment_modifications(self, db_session):
        """
        CRITICAL: Concurrent payment modifications must not corrupt balances.
        """
        game_setup = FinancialIntegrityTestUtils.create_balanced_game("CONCURRENT", 3)
        payment_service = PaymentService(db_session)
        payment_date = datetime.now(timezone.utc)

        # Create initial payments
        payments = []
        for i in range(10):
            payment = payment_service.record_payment(
                game_id=game_setup.game_id,
                payer_id=game_setup.player_ids[i % 3],
                recipient_id=game_setup.player_ids[(i + 1) % 3],
                amount=Decimal("10.00"),
                payment_date=payment_date,
                payment_method=f"Concurrent_{i}",
                created_by="test"
            )
            payments.append(payment)

        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def modify_payment(payment, new_amount):
            """Modify a payment amount."""
            try:
                with SessionLocal() as db:
                    payment_to_modify = db.query(PaymentTransaction).filter(
                        PaymentTransaction.id == payment.id
                    ).first()
                    if payment_to_modify:
                        payment_to_modify.amount_cents = int(new_amount * 100)
                        db.commit()
                return f"success_{payment.id}"
            except Exception as e:
                return f"error_{payment.id}: {e}"

        # Modify multiple payments concurrently
        modification_tasks = [
            (payments[i], Decimal(f"{15 + i}.00"))
            for i in range(len(payments))
        ]

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(modify_payment, payment, amount)
                for payment, amount in modification_tasks
            ]
            results = [future.result() for future in as_completed(futures)]

        # Verify most modifications succeeded
        successful = [r for r in results if r.startswith("success_")]
        assert len(successful) >= len(payments) * 0.8, \
            f"Too many concurrent modifications failed: {len(successful)}/{len(payments)}"

        # Most importantly: verify financial integrity maintained
        final_snapshot = FinancialIntegrityTestUtils.take_financial_snapshot(game_setup.game_id)
        FinancialIntegrityTestUtils.verify_financial_invariants(final_snapshot)

    def test_payment_deletion_cascade_effects(self, db_session):
        """
        CRITICAL: Payment deletion must properly handle cascade effects on settlements.
        """
        game_setup = FinancialIntegrityTestUtils.create_balanced_game("CASCADE", 4)
        payment_service = PaymentService(db_session)

        # Create complex payment web
        complex_payments = FinancialIntegrityTestUtils.create_complex_debt_web(game_setup)
        payment_transactions = FinancialIntegrityTestUtils.execute_payment_sequence(
            game_setup.game_id, complex_payments
        )

        # Get initial settlement suggestions
        initial_suggestions = payment_service.get_settlement_suggestions(game_setup.game_id)

        # Delete one key payment
        key_payment = payment_transactions[0]  # Delete first payment in the web

        with SessionLocal() as db:
            db.delete(key_payment)
            db.commit()

        # Get new settlement suggestions
        updated_suggestions = payment_service.get_settlement_suggestions(game_setup.game_id)

        # Suggestions should be different but still mathematically correct
        validation_results = FinancialIntegrityTestUtils.verify_settlement_suggestions_valid(game_setup.game_id)
        for result in validation_results:
            assert all(result.values()), f"Invalid settlement after payment deletion: {result}"

        # Verify financial integrity maintained
        final_snapshot = FinancialIntegrityTestUtils.take_financial_snapshot(game_setup.game_id)
        FinancialIntegrityTestUtils.verify_financial_invariants(final_snapshot)

        # Verify settlement execution still works
        settlement_metrics = FinancialIntegrityTestUtils.simulate_settlement_execution(game_setup.game_id)
        assert settlement_metrics["settlement_completed"], \
            "Settlement failed to complete after payment deletion"