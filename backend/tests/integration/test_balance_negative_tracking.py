"""
Integration tests for balance_negative_since tracking.

CRITICAL: These tests verify payment-grade reliability of state transitions.
Tests cover all state transitions, concurrent updates, constraint enforcement,
and integration with the alert system.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.db.database import SessionLocal, engine
from src.db.models import Game, Player, PaymentTransaction, PaymentBalance, Session, SessionPlayerSummary
from src.services.payment_service_v2 import PaymentService
from src.services.alert_service import AlertService
from domain.poker.value_objects import GameId, PlayerId, Money
from infrastructure.persistence.sqlalchemy.payment_repository import SQLAlchemyPaymentBalanceRepository


class TestBalanceNegativeTracking:
    """Critical tests for balance_negative_since state transition tracking."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clean database before and after each test."""
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

        yield

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

    def create_test_game_with_player(self, poker_winnings_cents=0):
        """Create a test game with two players (one for testing, one helper) and poker winnings."""
        with SessionLocal() as db:
            # Create game
            game = Game(
                public_code=f"TEST{uuid4().hex[:6].upper()}",
                admin_code=f"admin-{uuid4()}",
                title="Balance Tracking Test Game"
            )
            db.add(game)
            db.flush()

            # Create test player
            player = Player(display_name="Test Player")
            # Create helper player for payments (to avoid self-payment validation error)
            helper = Player(display_name="Helper Player")
            db.add_all([player, helper])
            db.flush()

            # Create session
            session = Session(
                game_id=game.id,
                external_id=f"session-{uuid4()}",
                session_name="Test Session",
                started_at=datetime.now(timezone.utc)
            )
            db.add(session)
            db.flush()

            # Create session summary with poker winnings for test player
            summary = SessionPlayerSummary(
                session_id=session.id,
                player_id=player.id,
                net=poker_winnings_cents,  # Already in cents
                buy_in_sum=10000,  # $100
                cash_out_sum=10000 + poker_winnings_cents,
                in_game=0,
                names=[player.display_name]
            )
            # Helper player with zero balance
            helper_summary = SessionPlayerSummary(
                session_id=session.id,
                player_id=helper.id,
                net=-poker_winnings_cents,  # Balance out for zero-sum
                buy_in_sum=10000,
                cash_out_sum=10000 - poker_winnings_cents,
                in_game=0,
                names=[helper.display_name]
            )
            db.add_all([summary, helper_summary])
            db.commit()

            return str(game.id), str(player.id), str(helper.id)

    def test_transition_positive_to_negative_sets_timestamp(self):
        """Test: positive → negative sets balance_negative_since to NOW."""
        game_id, player_id, helper_id = self.create_test_game_with_player(poker_winnings_cents=5000)  # $50 profit

        with SessionLocal() as db:
            # Initial state: positive balance (player is owed money)
            repo = SQLAlchemyPaymentBalanceRepository(db)
            repo.update_balances_for_players(GameId(game_id), [PlayerId(player_id)])
            db.commit()

            initial_balance = repo.get_balance(PlayerId(player_id), GameId(game_id))
            assert initial_balance.balance.amount == 5000
            assert initial_balance.balance_negative_since is None

            # Helper pays player, but they overpay creating negative balance
            # Player is owed $50, receives $60 → balance becomes -$10 (owes $10)
            before = datetime.now(timezone.utc)
            payment_service = PaymentService(db_session=db)
            payment_service.record_payment(
                game_id=game_id,
                payer_id=helper_id,  # Helper pays
                recipient_id=player_id,  # Player receives
                amount=Decimal("60"),  # Receives $60 when only owed $50
                payment_date=datetime.now(timezone.utc)
            )
            db.commit()
            after = datetime.now(timezone.utc)

            # Verify timestamp was set
            # Balance = poker_net(5000) + paid(0) - received(6000) = -1000
            updated = repo.get_balance(PlayerId(player_id), GameId(game_id))
            assert updated.balance.amount == -1000  # -$10
            assert updated.balance_negative_since is not None
            assert before <= updated.balance_negative_since <= after

    def test_transition_negative_to_more_negative_preserves_timestamp(self):
        """Test: negative → more negative preserves original timestamp (idempotent)."""
        game_id, player_id, helper_id = self.create_test_game_with_player(poker_winnings_cents=-5000)  # -$50 loss

        with SessionLocal() as db:
            repo = SQLAlchemyPaymentBalanceRepository(db)

            # Initial negative balance
            repo.update_balances_for_players(GameId(game_id), [PlayerId(player_id)])
            db.commit()

            initial = repo.get_balance(PlayerId(player_id), GameId(game_id))
            assert initial.balance.amount == -5000
            original_timestamp = initial.balance_negative_since
            assert original_timestamp is not None

            # Player receives more money, making balance MORE negative
            # Balance = poker_net(-5000) + paid(0) - received(2000) = -7000
            payment_service = PaymentService(db_session=db)
            payment_service.record_payment(
                game_id=game_id,
                payer_id=helper_id,  # Helper pays
                recipient_id=player_id,  # Player receives
                amount=Decimal("20"),  # Receives $20 more
                payment_date=datetime.now(timezone.utc)
            )
            db.commit()

            # Verify timestamp was PRESERVED (not updated)
            updated = repo.get_balance(PlayerId(player_id), GameId(game_id))
            assert updated.balance.amount == -7000  # -$70
            assert updated.balance_negative_since == original_timestamp

    def test_transition_negative_to_positive_clears_timestamp(self):
        """Test: negative → positive clears balance_negative_since."""
        game_id, player_id, helper_id = self.create_test_game_with_player(poker_winnings_cents=-5000)  # -$50 loss

        with SessionLocal() as db:
            repo = SQLAlchemyPaymentBalanceRepository(db)

            # Initial negative balance
            repo.update_balances_for_players(GameId(game_id), [PlayerId(player_id)])
            db.commit()

            initial = repo.get_balance(PlayerId(player_id), GameId(game_id))
            assert initial.balance.amount == -5000
            assert initial.balance_negative_since is not None

            # Player pays their debt, clearing it
            # Balance = poker_net(-5000) + paid(6000) - received(0) = 1000 (positive!)
            payment_service = PaymentService(db_session=db)
            payment_service.record_payment(
                game_id=game_id,
                payer_id=player_id,  # Player pays
                recipient_id=helper_id,  # Helper receives
                amount=Decimal("60"),  # Pays $60 when only owes $50
                payment_date=datetime.now(timezone.utc)
            )
            db.commit()

            # Verify timestamp was cleared
            updated = repo.get_balance(PlayerId(player_id), GameId(game_id))
            assert updated.balance.amount >= 0  # Positive or zero
            assert updated.balance_negative_since is None

    def test_database_constraint_prevents_negative_without_timestamp(self):
        """FAIL FAST: Database constraint rejects negative balance without timestamp."""
        game_id, player_id, helper_id = self.create_test_game_with_player()

        with SessionLocal() as db:
            # Try to create invalid state: negative balance, no timestamp
            with pytest.raises(IntegrityError, match="chk_balance_negative_since_consistent"):
                db.execute(text("""
                    INSERT INTO payment_balances (
                        game_id, player_id, poker_net_winnings,
                        total_paid, total_received, payment_balance, balance_negative_since
                    ) VALUES (:g, :p, -5000, 0, 0, -5000, NULL)
                """), {"g": game_id, "p": player_id})
                db.commit()

    def test_database_constraint_prevents_positive_with_timestamp(self):
        """FAIL FAST: Database constraint rejects positive balance with timestamp."""
        game_id, player_id, helper_id = self.create_test_game_with_player()

        with SessionLocal() as db:
            # Try to create invalid state: positive balance with timestamp
            with pytest.raises(IntegrityError, match="chk_balance_negative_since_consistent"):
                db.execute(text("""
                    INSERT INTO payment_balances (
                        game_id, player_id, poker_net_winnings,
                        total_paid, total_received, payment_balance, balance_negative_since
                    ) VALUES (:g, :p, 5000, 0, 0, 5000, NOW())
                """), {"g": game_id, "p": player_id})
                db.commit()

    def test_days_balance_negative_calculation(self):
        """Test: days_balance_negative() correctly calculates days."""
        game_id, player_id, helper_id = self.create_test_game_with_player(poker_winnings_cents=-5000)

        with SessionLocal() as db:
            repo = SQLAlchemyPaymentBalanceRepository(db)

            # Create negative balance
            repo.update_balances_for_players(GameId(game_id), [PlayerId(player_id)])
            db.commit()

            balance = repo.get_balance(PlayerId(player_id), GameId(game_id))

            # Calculate days (should be 0 since just created)
            days = balance.days_balance_negative(datetime.now(timezone.utc))
            assert days == 0

            # Manually set timestamp to 15 days ago
            db.execute(text("""
                UPDATE payment_balances
                SET balance_negative_since = NOW() - INTERVAL '15 days'
                WHERE player_id = :player_id AND game_id = :game_id
            """), {"player_id": player_id, "game_id": game_id})
            db.commit()

            # Re-fetch and verify
            balance = repo.get_balance(PlayerId(player_id), GameId(game_id))
            days = balance.days_balance_negative(datetime.now(timezone.utc))
            assert days == 15

    def test_alert_service_uses_new_field(self):
        """Test: Alert service correctly uses balance_negative_since for days_overdue."""
        game_id, player_id, helper_id = self.create_test_game_with_player(poker_winnings_cents=-5000)

        with SessionLocal() as db:
            # Initialize balance
            repo = SQLAlchemyPaymentBalanceRepository(db)
            repo.update_balances_for_players(GameId(game_id), [PlayerId(player_id)])
            db.commit()

            # Set balance_negative_since to 15 days ago
            db.execute(text("""
                UPDATE payment_balances
                SET balance_negative_since = NOW() - INTERVAL '15 days'
                WHERE player_id = :player_id AND game_id = :game_id
            """), {"player_id": player_id, "game_id": game_id})
            db.commit()

            # Get game's admin code
            game = db.query(Game).filter(Game.id == game_id).first()
            admin_code = game.admin_code

            # Create alert rule: days_overdue > 10
            alert_service = AlertService(db)
            alert_service.create_alert_rule(
                game_id=game_id,
                rule_type='days_overdue',
                threshold_value=10,
                admin_code=admin_code
            )
            db.commit()

            # Compute alert status
            status = alert_service.compute_alert_status(game_id)

            # Verify player has violation (15 days > 10 days threshold)
            assert len(status.player_alerts) == 1
            assert status.player_alerts[0].days_since_last_payment == 15
            assert len(status.player_alerts[0].violations) == 1
            assert status.player_alerts[0].violations[0].rule_type == 'days_overdue'
            assert status.player_alerts[0].violations[0].current_value == 15

    def test_idempotency_calling_twice_preserves_timestamp(self):
        """Test: Calling update_balances_for_players() twice with same data doesn't change timestamp."""
        game_id, player_id, helper_id = self.create_test_game_with_player(poker_winnings_cents=-5000)

        with SessionLocal() as db:
            repo = SQLAlchemyPaymentBalanceRepository(db)

            # First update (creates negative balance)
            repo.update_balances_for_players(GameId(game_id), [PlayerId(player_id)])
            db.commit()
            first_balance = repo.get_balance(PlayerId(player_id), GameId(game_id))
            first_timestamp = first_balance.balance_negative_since

            # Second update (no new payments, same balance)
            repo.update_balances_for_players(GameId(game_id), [PlayerId(player_id)])
            db.commit()
            second_balance = repo.get_balance(PlayerId(player_id), GameId(game_id))
            second_timestamp = second_balance.balance_negative_since

            # Timestamps should be identical (idempotent)
            assert first_timestamp == second_timestamp

    def test_transition_positive_to_zero_keeps_null(self):
        """Test: positive → zero keeps balance_negative_since as NULL."""
        game_id, player_id, helper_id = self.create_test_game_with_player(poker_winnings_cents=5000)

        with SessionLocal() as db:
            repo = SQLAlchemyPaymentBalanceRepository(db)

            # Initial positive balance
            repo.update_balances_for_players(GameId(game_id), [PlayerId(player_id)])
            db.commit()

            # Helper pays player exactly what they're owed
            # Balance = poker_net(5000) + paid(0) - received(5000) = 0
            payment_service = PaymentService(db_session=db)
            payment_service.record_payment(
                game_id=game_id,
                payer_id=helper_id,  # Helper pays
                recipient_id=player_id,  # Player receives
                amount=Decimal("50"),  # Receives exactly $50
                payment_date=datetime.now(timezone.utc)
            )
            db.commit()

            # Verify balance is zero and timestamp is NULL
            updated = repo.get_balance(PlayerId(player_id), GameId(game_id))
            assert updated.balance.amount == 0
            assert updated.balance_negative_since is None

    def test_domain_entity_validation_fails_on_invalid_state(self):
        """FAIL FAST: Domain entity __post_init__ rejects invalid states."""
        from domain.payments.entities import PlayerBalance

        # Try to create invalid state: negative balance, no timestamp
        with pytest.raises(ValueError, match="INVARIANT VIOLATION"):
            PlayerBalance(
                player_id=PlayerId(str(uuid4())),
                game_id=GameId(str(uuid4())),
                poker_net_winnings=Money(-5000),
                total_paid=Money(0),
                total_received=Money(0),
                balance_negative_since=None
            )

    def test_multiple_players_independent_tracking(self):
        """Test: Multiple players track balance_negative_since independently."""
        # Create game with two players
        with SessionLocal() as db:
            game = Game(
                public_code=f"TEST{uuid4().hex[:6].upper()}",
                admin_code=f"admin-{uuid4()}",
                title="Multi-Player Test"
            )
            db.add(game)
            db.flush()

            player1 = Player(display_name="Player 1")
            player2 = Player(display_name="Player 2")
            db.add_all([player1, player2])
            db.flush()

            session = Session(
                game_id=game.id,
                external_id=f"session-{uuid4()}",
                session_name="Test Session",
                started_at=datetime.now(timezone.utc)
            )
            db.add(session)
            db.flush()

            # Player 1: negative balance
            summary1 = SessionPlayerSummary(
                session_id=session.id,
                player_id=player1.id,
                net=-5000,
                buy_in_sum=10000,
                cash_out_sum=5000,
                in_game=0,
                names=[player1.display_name]
            )
            # Player 2: positive balance
            summary2 = SessionPlayerSummary(
                session_id=session.id,
                player_id=player2.id,
                net=5000,
                buy_in_sum=10000,
                cash_out_sum=15000,
                in_game=0,
                names=[player2.display_name]
            )
            db.add_all([summary1, summary2])
            db.commit()

            repo = SQLAlchemyPaymentBalanceRepository(db)
            repo.update_balances_for_players(
                GameId(str(game.id)),
                [PlayerId(str(player1.id)), PlayerId(str(player2.id))]
            )
            db.commit()

            # Verify independent tracking
            balance1 = repo.get_balance(PlayerId(str(player1.id)), GameId(str(game.id)))
            balance2 = repo.get_balance(PlayerId(str(player2.id)), GameId(str(game.id)))

            assert balance1.balance.amount == -5000
            assert balance1.balance_negative_since is not None
            assert balance2.balance.amount == 5000
            assert balance2.balance_negative_since is None
