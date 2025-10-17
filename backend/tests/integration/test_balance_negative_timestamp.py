"""
Integration Tests for balance_negative_since Timestamp Tracking

Tests the fix for the "days balance negative" bug where timestamps were being
incorrectly reset to the current time during balance recalculations.

Key scenarios tested:
1. Initial timestamp set when balance first becomes negative
2. Timestamp preserved when balance stays negative
3. Timestamp cleared when balance returns to positive
4. Fail-fast on missing timestamps during negative → negative transitions
"""

import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from src.db.database import SessionLocal
from src.db.models import Game, Player, Session, SessionPlayerSummary, PaymentTransaction, PaymentBalance
from src.services.payment_service_v2 import PaymentService
from src.infrastructure.persistence.sqlalchemy.payment_repository import SQLAlchemyPaymentBalanceRepository
from src.domain.poker.value_objects import GameId, PlayerId, Money


class TestBalanceNegativeTimestamp:
    """Test balance_negative_since timestamp tracking."""

    @pytest.fixture
    def timestamp_setup(self, db_session):
        """Setup game with players and session data for timestamp tests."""
        # Create game with unique codes
        unique_id = str(uuid.uuid4())[:8].upper()
        game = Game(
            public_code=f"TS{unique_id}",
            admin_code=f"ADM{unique_id}",
            title=f"Timestamp Test Game {unique_id}"
        )
        db_session.add(game)
        db_session.flush()

        # Create two players
        alice = Player(
            display_name=f"Alice_{unique_id}",
            external_id=f"alice_ts_{unique_id}"
        )
        bob = Player(
            display_name=f"Bob_{unique_id}",
            external_id=f"bob_ts_{unique_id}"
        )
        db_session.add(alice)
        db_session.add(bob)
        db_session.flush()

        # Create session with poker results: Alice wins $100, Bob loses $100
        session = Session(
            game_id=game.id,
            external_id=f"ts_session_{unique_id}",
            session_type="cash_game"
        )
        db_session.add(session)
        db_session.flush()

        # Alice wins $100
        alice_summary = SessionPlayerSummary(
            session_id=session.id,
            player_id=alice.id,
            buy_in_sum=100000,  # $1000
            cash_out_sum=110000,  # $1100
            in_game=0,
            net=10000,  # +$100
            names=[alice.display_name]
        )
        db_session.add(alice_summary)

        # Bob loses $100
        bob_summary = SessionPlayerSummary(
            session_id=session.id,
            player_id=bob.id,
            buy_in_sum=100000,  # $1000
            cash_out_sum=90000,  # $900
            in_game=0,
            net=-10000,  # -$100
            names=[bob.display_name]
        )
        db_session.add(bob_summary)

        db_session.commit()
        return game, alice, bob

    def test_timestamp_set_when_balance_becomes_negative(self, timestamp_setup, db_session):
        """When a balance first becomes negative, timestamp should be set to NOW."""
        game, alice, bob = timestamp_setup

        service = PaymentService(db_session)

        # Get initial balances - should trigger balance calculation
        # Bob has negative balance (-$100 from poker losses)
        summary = service.get_payment_summary(str(game.id))
        bob_summary = next(p for p in summary if p.player_id == str(bob.id))

        # Bob should have negative balance
        assert bob_summary.balance == Decimal('-100.00')

        # Check the database for balance_negative_since timestamp
        balance_record = db_session.query(PaymentBalance).filter(
            PaymentBalance.player_id == bob.id,
            PaymentBalance.game_id == game.id
        ).first()

        assert balance_record is not None
        assert balance_record.balance_negative_since is not None

        # Timestamp should be recent (within last minute)
        time_diff = datetime.now(timezone.utc) - balance_record.balance_negative_since
        assert time_diff < timedelta(minutes=1)

    def test_timestamp_preserved_when_balance_stays_negative(self, timestamp_setup, db_session):
        """When balance stays negative, timestamp should NOT be reset."""
        game, alice, bob = timestamp_setup

        service = PaymentService(db_session)

        # Initial balance calculation - Bob has -$100
        summary = service.get_payment_summary(str(game.id))
        bob_summary = next(p for p in summary if p.player_id == str(bob.id))
        assert bob_summary.balance == Decimal('-100.00')

        # Get initial timestamp
        balance_record = db_session.query(PaymentBalance).filter(
            PaymentBalance.player_id == bob.id,
            PaymentBalance.game_id == game.id
        ).first()
        original_timestamp = balance_record.balance_negative_since
        assert original_timestamp is not None

        # Wait a moment to ensure timestamps would differ if reset
        import time
        time.sleep(0.1)

        # Record a payment that keeps Bob negative (but less negative)
        # Bob pays Alice $20, so balance goes from -$100 to -$80
        service.record_payment(
            game_id=str(game.id),
            payer_id=str(bob.id),
            recipient_id=str(alice.id),
            amount=Decimal('20.00'),
            payment_date=datetime.now(timezone.utc)
        )

        # Check that timestamp was PRESERVED (not reset)
        db_session.refresh(balance_record)
        new_timestamp = balance_record.balance_negative_since

        assert new_timestamp is not None
        assert new_timestamp == original_timestamp, "Timestamp should be preserved during negative→negative transition"

        # Verify balance changed but timestamp didn't
        assert balance_record.payment_balance == -8000  # -$80 in cents

    def test_timestamp_cleared_when_balance_becomes_positive(self, timestamp_setup, db_session):
        """When balance returns to positive/zero, timestamp should be cleared."""
        game, alice, bob = timestamp_setup

        service = PaymentService(db_session)

        # Initial balance calculation - Bob has -$100
        summary = service.get_payment_summary(str(game.id))
        bob_summary = next(p for p in summary if p.player_id == str(bob.id))
        assert bob_summary.balance == Decimal('-100.00')

        # Verify timestamp exists
        balance_record = db_session.query(PaymentBalance).filter(
            PaymentBalance.player_id == bob.id,
            PaymentBalance.game_id == game.id
        ).first()
        assert balance_record.balance_negative_since is not None

        # Bob pays Alice $100, settling his debt
        service.record_payment(
            game_id=str(game.id),
            payer_id=str(bob.id),
            recipient_id=str(alice.id),
            amount=Decimal('100.00'),
            payment_date=datetime.now(timezone.utc)
        )

        # Timestamp should be cleared (NULL)
        db_session.refresh(balance_record)
        assert balance_record.balance_negative_since is None
        assert balance_record.payment_balance == 0  # $0 balance

    def test_timestamp_stays_null_when_balance_stays_positive(self, timestamp_setup, db_session):
        """When balance is positive and stays positive, timestamp should remain NULL."""
        game, alice, bob = timestamp_setup

        service = PaymentService(db_session)

        # Initial balance calculation - Alice has +$100 (is owed money)
        summary = service.get_payment_summary(str(game.id))
        alice_summary = next(p for p in summary if p.player_id == str(alice.id))
        assert alice_summary.balance == Decimal('100.00')

        # Verify timestamp is NULL
        balance_record = db_session.query(PaymentBalance).filter(
            PaymentBalance.player_id == alice.id,
            PaymentBalance.game_id == game.id
        ).first()
        assert balance_record.balance_negative_since is None

        # Bob pays Alice $50 (Alice still owed $50, still positive)
        service.record_payment(
            game_id=str(game.id),
            payer_id=str(bob.id),
            recipient_id=str(alice.id),
            amount=Decimal('50.00'),
            payment_date=datetime.now(timezone.utc)
        )

        # Timestamp should still be NULL
        db_session.refresh(balance_record)
        assert balance_record.balance_negative_since is None
        assert balance_record.payment_balance == 5000  # $50 in cents

    def test_fail_fast_on_missing_timestamp_with_negative_balance(self, timestamp_setup, db_session):
        """If a player has negative balance but NULL timestamp, update should fail fast."""
        game, alice, bob = timestamp_setup

        # Manually corrupt the data: Set Bob's balance to negative but clear the timestamp
        balance_record = db_session.query(PaymentBalance).filter(
            PaymentBalance.player_id == bob.id,
            PaymentBalance.game_id == game.id
        ).first()

        if balance_record is None:
            # Create balance record with corrupted data
            balance_record = PaymentBalance(
                game_id=game.id,
                player_id=bob.id,
                poker_net_winnings=-10000,  # -$100
                total_paid=0,
                total_received=0,
                payment_balance=-10000,  # -$100
                balance_negative_since=None  # CORRUPTED: NULL despite negative balance
            )
            db_session.add(balance_record)
        else:
            balance_record.balance_negative_since = None  # Corrupt existing record

        db_session.commit()

        # Now try to update balances - should fail fast with invariant violation
        repository = SQLAlchemyPaymentBalanceRepository(db_session)

        with pytest.raises(ValueError, match="INVARIANT VIOLATION"):
            repository.update_balances_for_players(
                GameId(str(game.id)),
                [PlayerId(str(bob.id))]
            )

    def test_multiple_negative_transitions_preserve_original_timestamp(self, timestamp_setup, db_session):
        """Multiple balance changes while negative should all preserve the original timestamp."""
        game, alice, bob = timestamp_setup

        service = PaymentService(db_session)

        # Initial balance calculation - Bob has -$100
        summary = service.get_payment_summary(str(game.id))
        bob_summary = next(p for p in summary if p.player_id == str(bob.id))
        assert bob_summary.balance == Decimal('-100.00')

        # Get original timestamp
        balance_record = db_session.query(PaymentBalance).filter(
            PaymentBalance.player_id == bob.id,
            PaymentBalance.game_id == game.id
        ).first()
        original_timestamp = balance_record.balance_negative_since
        assert original_timestamp is not None

        # Make several payments that keep Bob negative
        import time

        # Payment 1: Bob pays $10 (balance: -$90)
        time.sleep(0.05)
        service.record_payment(
            game_id=str(game.id),
            payer_id=str(bob.id),
            recipient_id=str(alice.id),
            amount=Decimal('10.00'),
            payment_date=datetime.now(timezone.utc)
        )
        db_session.refresh(balance_record)
        assert balance_record.balance_negative_since == original_timestamp

        # Payment 2: Bob pays $20 (balance: -$70)
        time.sleep(0.05)
        service.record_payment(
            game_id=str(game.id),
            payer_id=str(bob.id),
            recipient_id=str(alice.id),
            amount=Decimal('20.00'),
            payment_date=datetime.now(timezone.utc)
        )
        db_session.refresh(balance_record)
        assert balance_record.balance_negative_since == original_timestamp

        # Payment 3: Bob pays $30 (balance: -$40)
        time.sleep(0.05)
        service.record_payment(
            game_id=str(game.id),
            payer_id=str(bob.id),
            recipient_id=str(alice.id),
            amount=Decimal('30.00'),
            payment_date=datetime.now(timezone.utc)
        )
        db_session.refresh(balance_record)
        assert balance_record.balance_negative_since == original_timestamp

        # Verify final state
        assert balance_record.payment_balance == -4000  # -$40 in cents
        assert balance_record.balance_negative_since == original_timestamp


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
