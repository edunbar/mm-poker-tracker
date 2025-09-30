"""
Comprehensive Integration Tests for Payment Service

Tests the complete payment service functionality including:
- Core payment recording with validation
- Balance calculations and financial integrity
- Settlement optimization
- Error handling and edge cases
- Data integrity and concurrency
"""

import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import time

from src.db.database import SessionLocal
from src.db.models import Game, Player, Session, SessionPlayerSummary, PaymentTransaction, PaymentBalance
from src.services.payment_service import PaymentService as OldPaymentService

# Use the new service for testing since it's now fully compatible
from src.services.payment_service_v2 import PaymentService as PaymentService


class TestPaymentRecording:
    """Core payment recording functionality tests."""

    @pytest.fixture
    def payment_setup(self):
        """Setup game with players and session data for payment tests."""
        db = SessionLocal()
        try:
            # Create game with unique codes
            unique_id = str(uuid.uuid4())[:8].upper()
            game = Game(
                public_code=f"TEST{unique_id}",
                admin_code=f"ADM{unique_id}",
                title=f"Payment Test Game {unique_id}"
            )
            db.add(game)
            db.flush()

            # Create players
            players = []
            for i, name in enumerate(["Alice", "Bob", "Charlie", "David"]):
                player = Player(
                    display_name=f"{name}_{unique_id}",
                    external_id=f"player_{i+1}_test_{unique_id}"
                )
                db.add(player)
                players.append(player)
            db.flush()

            # Create session with poker winnings
            session = Session(
                game_id=game.id,
                external_id=f"test_session_payments_{unique_id}",
                session_type="cash_game"
            )
            db.add(session)
            db.flush()

            # Give players different poker results
            poker_results = [50000, -10000, -20000, -20000]  # $500, -$100, -$200, -$200 (sums to 0)
            for i, player in enumerate(players):
                summary = SessionPlayerSummary(
                    session_id=session.id,
                    player_id=player.id,
                    buy_in_sum=100000,  # $1000
                    cash_out_sum=100000 + poker_results[i],
                    in_game=0,
                    net=poker_results[i],
                    names=[player.display_name]
                )
                db.add(summary)

            db.commit()
            yield game, players, session

        finally:
            db.close()

    def test_record_simple_payment(self, payment_setup, db_session):
        """Basic payment between two players."""
        game, players, session = payment_setup
        alice, bob = players[0], players[1]

        service = PaymentService(db_session)

        # Record payment: Bob pays Alice $100
        payment_date = datetime.now(timezone.utc)
        result = service.record_payment(
            game_id=str(game.id),
            payer_id=str(bob.id),
            recipient_id=str(alice.id),
            amount=Decimal('100.00'),
            payment_date=payment_date,
            payment_method="Venmo",
            notes="Test payment",
            reference_id="venmo_12345"
        )

        # Verify payment saved correctly
        assert str(result.game_id) == str(game.id)
        assert str(result.payer_id) == str(bob.id)
        assert str(result.recipient_id) == str(alice.id)
        assert result.amount_cents == 10000  # $100.00 in cents
        assert result.payment_method == "Venmo"
        assert result.notes == "Test payment"
        assert result.reference_id == "venmo_12345"

        # Verify balances updated
        summary = service.get_payment_summary(str(game.id))
        alice_summary = next(p for p in summary if p.player_id == str(alice.id))
        bob_summary = next(p for p in summary if p.player_id == str(bob.id))

        # Alice: won $500, received $100 from Bob, paid $0
        # Balance = poker_net_winnings + total_paid - total_received = 500 + 0 - 100 = 400
        # Alice is still owed $400
        assert alice_summary.total_received == Decimal('100.00')
        assert alice_summary.poker_net_winnings == Decimal('500.00')
        assert alice_summary.balance == Decimal('400.00')

        # Bob: lost $100 at poker, paid $100 to Alice, received $0
        # Balance = poker_net_winnings + total_paid - total_received = (-100) + 100 - 0 = 0
        # Bob paid his debt, so balance is 0
        assert bob_summary.total_paid == Decimal('100.00')
        assert bob_summary.poker_net_winnings == Decimal('-100.00')
        assert bob_summary.balance == Decimal('0.00')  # Bob paid his debt

        # Realized earnings = actual cash flow (received - paid)
        assert alice_summary.realized_earnings == Decimal('100.00')  # Received $100, paid $0
        assert bob_summary.realized_earnings == Decimal('-100.00')   # Received $0, paid $100

    def test_prevent_self_payment(self, payment_setup, db_session):
        """Cannot pay yourself."""
        game, players, _ = payment_setup
        alice = players[0]

        service = PaymentService(db_session)

        with pytest.raises(ValueError, match="Payer and recipient cannot be the same"):
            service.record_payment(
                game_id=str(game.id),
                payer_id=str(alice.id),
                recipient_id=str(alice.id),
                amount=Decimal('100.00'),
                payment_date=datetime.now(timezone.utc)
            )

    def test_reject_negative_payment(self, payment_setup, db_session):
        """Cannot record negative amounts."""
        game, players, _ = payment_setup
        alice, bob = players[0], players[1]

        service = PaymentService(db_session)

        with pytest.raises(ValueError, match="Payment amount must be positive"):
            service.record_payment(
                game_id=str(game.id),
                payer_id=str(bob.id),
                recipient_id=str(alice.id),
                amount=Decimal('-50.00'),
                payment_date=datetime.now(timezone.utc)
            )

    def test_reject_zero_payment(self, payment_setup, db_session):
        """Cannot record zero amount payment."""
        game, players, _ = payment_setup
        alice, bob = players[0], players[1]

        service = PaymentService(db_session)

        with pytest.raises(ValueError, match="Payment amount must be positive"):
            service.record_payment(
                game_id=str(game.id),
                payer_id=str(bob.id),
                recipient_id=str(alice.id),
                amount=Decimal('0.00'),
                payment_date=datetime.now(timezone.utc)
            )

    def test_payment_with_nonexistent_player(self, payment_setup, db_session):
        """Verify proper error when player doesn't exist."""
        game, players, _ = payment_setup
        alice = players[0]
        fake_player_id = str(uuid.uuid4())

        service = PaymentService(db_session)

        with pytest.raises(ValueError, match="not found"):
            service.record_payment(
                game_id=str(game.id),
                payer_id=str(alice.id),
                recipient_id=fake_player_id,
                amount=Decimal('100.00'),
                payment_date=datetime.now(timezone.utc)
            )

    def test_payment_with_nonexistent_game(self, payment_setup, db_session):
        """Verify proper error when game doesn't exist."""
        _, players, _ = payment_setup
        alice, bob = players[0], players[1]
        fake_game_id = str(uuid.uuid4())

        service = PaymentService(db_session)

        with pytest.raises(ValueError, match="Game .* not found"):
            service.record_payment(
                game_id=fake_game_id,
                payer_id=str(bob.id),
                recipient_id=str(alice.id),
                amount=Decimal('100.00'),
                payment_date=datetime.now(timezone.utc)
            )


class TestBalanceCalculations:
    """Test balance calculation logic and financial integrity."""

    @pytest.fixture
    def balance_setup(self):
        """Setup for balance calculation tests."""
        db = SessionLocal()
        try:
            unique_id = str(uuid.uuid4())[:8].upper()
            game = Game(
                public_code=f"BAL{unique_id}",
                admin_code=f"ADMIN{unique_id}",
                title=f"Balance Test {unique_id}"
            )
            db.add(game)
            db.flush()

            # Create 3 players
            players = []
            for name in ["Alice", "Bob", "Charlie"]:
                player = Player(
                    display_name=f"{name}_{unique_id}",
                    external_id=f"{name.lower()}_balance_test_{unique_id}"
                )
                db.add(player)
                players.append(player)
            db.flush()

            # Create session with winnings: Alice +$200, Bob -$100, Charlie -$100
            session = Session(game_id=game.id, external_id=f"balance_session_{unique_id}", session_type="cash_game")
            db.add(session)
            db.flush()

            winnings = [20000, -10000, -10000]  # Cents
            for player, net in zip(players, winnings):
                summary = SessionPlayerSummary(
                    session_id=session.id,
                    player_id=player.id,
                    buy_in_sum=100000,
                    cash_out_sum=100000 + net,
                    in_game=0,
                    net=net,
                    names=[player.display_name]
                )
                db.add(summary)

            db.commit()
            yield game, players

        finally:
            db.close()

    def test_balance_after_poker_winnings_only(self, balance_setup, db_session):
        """Balance = received - poker_net_winnings (negative means player owes money)."""
        game, players = balance_setup
        alice, bob, charlie = players

        service = PaymentService(db_session)

        # Get payment summary (V2 service automatically calculates balances)
        summary = service.get_payment_summary(str(game.id))

        # Find player summaries
        alice_summary = next(p for p in summary if p.player_id == str(alice.id))
        bob_summary = next(p for p in summary if p.player_id == str(bob.id))
        charlie_summary = next(p for p in summary if p.player_id == str(charlie.id))

        # Alice won $200, no payments yet -> balance = 200 + 0 - 0 = +$200 (is owed $200)
        assert alice_summary.poker_net_winnings == Decimal('200.00')
        assert alice_summary.total_received == Decimal('0.00')
        assert alice_summary.balance == Decimal('200.00')

        # Bob lost $100, no payments yet -> balance = -100 + 0 - 0 = -$100 (owes $100)
        assert bob_summary.poker_net_winnings == Decimal('-100.00')
        assert bob_summary.balance == Decimal('-100.00')

        # Charlie lost $100 -> balance = -$100 (owes $100)
        assert charlie_summary.balance == Decimal('-100.00')

    def test_balance_after_receiving_payment(self, balance_setup, db_session):
        """Receiving payment reduces what you're owed."""
        game, players = balance_setup
        alice, bob = players[0], players[1]

        service = PaymentService(db_session)

        # Alice owes $200, receives $80 from Bob
        service.record_payment(
            game_id=str(game.id),
            payer_id=str(bob.id),
            recipient_id=str(alice.id),
            amount=Decimal('80.00'),
            payment_date=datetime.now(timezone.utc)
        )

        summary = service.get_payment_summary(str(game.id))
        alice_summary = next(p for p in summary if p.player_id == str(alice.id))

        # Alice: won $200, received $80 -> balance = 200 + 0 - 80 = +$120 (still owed $120)
        assert alice_summary.total_received == Decimal('80.00')
        assert alice_summary.balance == Decimal('120.00')

    def test_realized_earnings_calculation(self, balance_setup, db_session):
        """Realized = received - paid (actual cash flow)."""
        game, players = balance_setup
        alice, bob = players[0], players[1]

        service = PaymentService(db_session)

        # Bob pays Alice $50, then Alice pays Bob $20
        service.record_payment(
            game_id=str(game.id),
            payer_id=str(bob.id),
            recipient_id=str(alice.id),
            amount=Decimal('50.00'),
            payment_date=datetime.now(timezone.utc)
        )

        service.record_payment(
            game_id=str(game.id),
            payer_id=str(alice.id),
            recipient_id=str(bob.id),
            amount=Decimal('20.00'),
            payment_date=datetime.now(timezone.utc)
        )

        summary = service.get_payment_summary(str(game.id))
        alice_summary = next(p for p in summary if p.player_id == str(alice.id))
        bob_summary = next(p for p in summary if p.player_id == str(bob.id))

        # Alice: received $50, paid $20 -> realized = $30
        assert alice_summary.realized_earnings == Decimal('30.00')

        # Bob: received $20, paid $50 -> realized = -$30
        assert bob_summary.realized_earnings == Decimal('-30.00')

    def test_zero_sum_validation(self, balance_setup, db_session):
        """All balances should sum to zero (money conservation)."""
        game, players = balance_setup
        alice, bob, charlie = players

        service = PaymentService(db_session)

        # Create various payments
        service.record_payment(
            game_id=str(game.id),
            payer_id=str(alice.id),
            recipient_id=str(bob.id),
            amount=Decimal('150.00'),
            payment_date=datetime.now(timezone.utc)
        )

        service.record_payment(
            game_id=str(game.id),
            payer_id=str(alice.id),
            recipient_id=str(charlie.id),
            amount=Decimal('50.00'),
            payment_date=datetime.now(timezone.utc)
        )

        # Verify zero sum
        summary = service.get_payment_summary(str(game.id))
        total_balance = sum(p.balance for p in summary)

        # Should be exactly zero (or very close due to rounding)
        assert abs(total_balance) < Decimal('0.01')


class TestSettlementOptimization:
    """Test settlement suggestion algorithms."""

    @pytest.fixture
    def settlement_setup(self):
        """Setup for settlement tests."""
        db = SessionLocal()
        try:
            unique_id = str(uuid.uuid4())[:8].upper()
            game = Game(
                public_code=f"SETT{unique_id}",
                admin_code=f"ADMIN{unique_id}",
                title=f"Settlement Test {unique_id}"
            )
            db.add(game)
            db.flush()

            # Create 4 players with unique IDs
            players = []
            for name in ["Alice", "Bob", "Charlie", "David"]:
                player = Player(
                    display_name=f"{name}_{unique_id}",
                    external_id=f"{name.lower()}_settlement_{unique_id}"
                )
                db.add(player)
                players.append(player)
            db.flush()

            # Session with: Alice +$300, Bob -$100, Charlie -$100, David -$100
            session = Session(
                game_id=game.id,
                external_id=f"settlement_session_{unique_id}",
                session_type="cash_game"
            )
            db.add(session)
            db.flush()

            winnings = [30000, -10000, -10000, -10000]  # Cents
            for player, net in zip(players, winnings):
                summary = SessionPlayerSummary(
                    session_id=session.id,
                    player_id=player.id,
                    buy_in_sum=100000,
                    cash_out_sum=100000 + net,
                    in_game=0,
                    net=net,
                    names=[player.display_name]
                )
                db.add(summary)

            db.commit()
            yield game, players

        finally:
            db.close()

    def test_simple_settlement_scenario(self, settlement_setup, db_session):
        """Basic settlement optimization."""
        game, players = settlement_setup

        service = PaymentService(db_session)

        # V2 service automatically calculates balances

        suggestions = service.get_settlement_suggestions(str(game.id))

        # Should suggest 3 payments: Bob->Alice $100, Charlie->Alice $100, David->Alice $100
        # (or some equivalent optimal arrangement)
        assert len(suggestions) <= 3  # Optimal should be at most 3 payments

        # Verify total suggested payments equal total debts
        total_suggested = sum(s.amount for s in suggestions)
        assert total_suggested == Decimal('300.00')  # Alice is owed $300 total

    def test_settlement_preserves_balances(self, settlement_setup, db_session):
        """Settlement suggestions preserve the balance relationships."""
        game, players = settlement_setup
        alice = players[0]  # Alice won $300

        service = PaymentService(db_session)

        # V2 service automatically calculates balances

        suggestions = service.get_settlement_suggestions(str(game.id))

        # All suggestions should pay Alice (she's the only creditor)
        for suggestion in suggestions:
            assert suggestion.recipient_id == str(alice.id)

        # Sum of suggestions should equal what Alice is owed
        total_to_alice = sum(s.amount for s in suggestions)
        assert total_to_alice == Decimal('300.00')


class TestErrorHandling:
    """Test error scenarios and edge cases."""

    @pytest.fixture
    def error_setup(self):
        """Minimal setup for error testing."""
        db = SessionLocal()
        try:
            unique_id = str(uuid.uuid4())[:8].upper()
            game = Game(
                public_code=f"ERR{unique_id}",
                admin_code=f"ADMIN{unique_id}",
                title=f"Error Test {unique_id}"
            )
            db.add(game)
            db.flush()

            player = Player(
                display_name=f"TestPlayer_{unique_id}",
                external_id=f"test_error_player_{unique_id}"
            )
            db.add(player)
            db.flush()

            # Add session data so V2 service recognizes player connection to game
            session = Session(
                game_id=game.id,
                external_id=f"session_error_{unique_id}",
                game_number=1,
                started_at=datetime.now(timezone.utc),
                ended_at=datetime.now(timezone.utc)
            )
            db.add(session)
            db.flush()

            summary = SessionPlayerSummary(
                session_id=session.id,
                player_id=player.id,
                buy_in_sum=10000,
                cash_out_sum=10000,
                in_game=0,
                net=0,
                names=[player.display_name]
            )
            db.add(summary)

            db.commit()
            yield game, player
        finally:
            db.close()

    def test_payment_with_invalid_decimal(self, error_setup, db_session):
        """Handle invalid decimal amounts gracefully."""
        game, player = error_setup
        service = PaymentService(db_session)

        # Create second player for the test
        db = SessionLocal()
        try:
            # Generate unique ID for this player
            player2_unique_id = str(uuid.uuid4())[:8].upper()
            player2 = Player(
                display_name=f"Player2_{player2_unique_id}",
                external_id=f"test_player_2_{player2_unique_id}"
            )
            db.add(player2)
            db.flush()

            # Add session summary so V2 recognizes player2 connection to game
            session = db.query(Session).filter(Session.game_id == game.id).first()
            summary = SessionPlayerSummary(
                session_id=session.id,
                player_id=player2.id,
                buy_in_sum=10000,
                cash_out_sum=10000,
                in_game=0,
                net=0,
                names=[player2.display_name]
            )
            db.add(summary)
            db.commit()

            # Test with excess decimal precision (should be quantized gracefully)
            result = service.record_payment(
                game_id=str(game.id),
                payer_id=str(player.id),
                recipient_id=str(player2.id),
                amount=Decimal('100.999'),  # Too many decimal places -> quantized to 101.00
                payment_date=datetime.now(timezone.utc)
            )
            # Verify it was quantized to proper precision
            assert result.amount == Decimal('101.00')  # Rounded up due to ROUND_HALF_UP
        finally:
            db.close()

    def test_payment_date_timezone_handling(self, error_setup, db_session):
        """Verify timezone handling for payment dates."""
        game, player = error_setup
        service = PaymentService(db_session)

        db = SessionLocal()
        try:
            # Generate unique ID for timezone test player
            tz_unique_id = str(uuid.uuid4())[:8].upper()
            player2 = Player(
                display_name=f"Player2_{tz_unique_id}",
                external_id=f"test_player_2_tz_{tz_unique_id}"
            )
            db.add(player2)
            db.flush()

            # Add session summary so V2 recognizes player2 connection to game
            session = db.query(Session).filter(Session.game_id == game.id).first()
            summary = SessionPlayerSummary(
                session_id=session.id,
                player_id=player2.id,
                buy_in_sum=10000,
                cash_out_sum=10000,
                in_game=0,
                net=0,
                names=[player2.display_name]
            )
            db.add(summary)
            db.commit()

            # Test with different timezone
            payment_date = datetime.now().replace(tzinfo=timezone(timedelta(hours=5)))  # UTC+5

            result = service.record_payment(
                game_id=str(game.id),
                payer_id=str(player.id),
                recipient_id=str(player2.id),
                amount=Decimal('50.00'),
                payment_date=payment_date
            )

            # Should be stored and handled correctly
            assert result.payment_date is not None

        finally:
            db.close()


class TestDataIntegrity:
    """Test data integrity and consistency."""

    @pytest.fixture
    def integrity_setup(self):
        """Setup for data integrity tests."""
        db = SessionLocal()
        try:
            unique_id = str(uuid.uuid4())[:8].upper()
            game = Game(
                public_code=f"INT{unique_id}",
                admin_code=f"ADMIN{unique_id}",
                title=f"Integrity Test {unique_id}"
            )
            db.add(game)
            db.flush()

            players = []
            for name in ["Alice", "Bob"]:
                player = Player(
                    display_name=f"{name}_{unique_id}",
                    external_id=f"{name.lower()}_integrity_{unique_id}"
                )
                db.add(player)
                players.append(player)
            db.flush()

            # Add session data so V2 service recognizes player connections
            session = Session(
                game_id=game.id,
                external_id=f"session_integrity_{unique_id}",
                game_number=1,
                started_at=datetime.now(timezone.utc),
                ended_at=datetime.now(timezone.utc)
            )
            db.add(session)
            db.flush()

            for player in players:
                summary = SessionPlayerSummary(
                    session_id=session.id,
                    player_id=player.id,
                    buy_in_sum=10000,
                    cash_out_sum=10000,
                    in_game=0,
                    net=0,
                    names=[player.display_name]
                )
                db.add(summary)

            db.commit()
            yield game, players
        finally:
            db.close()

    def test_decimal_precision_preservation(self, integrity_setup, db_session):
        """No precision loss in decimal operations."""
        game, players = integrity_setup
        alice, bob = players

        service = PaymentService(db_session)

        # Payment with specific decimal precision
        result = service.record_payment(
            game_id=str(game.id),
            payer_id=str(bob.id),
            recipient_id=str(alice.id),
            amount=Decimal('123.45'),  # Exactly 123.45
            payment_date=datetime.now(timezone.utc)
        )

        # Verify exact precision preserved
        assert result.amount == Decimal('123.45')

        # Commit the payment so it can be queried in a new session
        db_session.commit()

        # Verify in database as cents
        db = SessionLocal()
        try:
            payment = db.query(PaymentTransaction).filter_by(id=result.id).first()
            assert payment is not None, "Payment not found in database"
            assert payment.amount_cents == 12345  # Exactly 12345 cents
        finally:
            db.close()



if __name__ == "__main__":
    pytest.main([__file__, "-v"])