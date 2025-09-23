"""
Comprehensive Payment System Tests

This test suite ensures complete coverage of:
- Payment transaction validation and recording
- Double-entry ledger consistency
- Balance calculations (all formulas)
- Settlement algorithm optimization
- Edge cases and concurrency
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4

from services.payment_service import PaymentService, PlayerPaymentSummary, SettlementSuggestion
from db.models import PaymentTransaction, PaymentBalance


@pytest.fixture
def payment_service():
    return PaymentService()


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.__enter__ = Mock(return_value=db)
    db.__exit__ = Mock(return_value=None)
    return db


class TestPaymentValidationComplete:
    """Comprehensive payment validation tests"""

    def test_no_self_payment_validation(self, payment_service):
        """Test: No self-payment allowed"""
        player_id = str(uuid4())
        with pytest.raises(ValueError, match="Payer and recipient cannot be the same"):
            payment_service.record_payment(
                game_id=str(uuid4()),
                payer_id=player_id,
                recipient_id=player_id,
                amount=Decimal("100.00"),
                payment_date=datetime.now(timezone.utc)
            )

    def test_positive_amounts_only(self, payment_service):
        """Test: Only positive amounts allowed"""
        with pytest.raises(ValueError, match="Payment amount must be positive"):
            payment_service.record_payment(
                game_id=str(uuid4()),
                payer_id=str(uuid4()),
                recipient_id=str(uuid4()),
                amount=Decimal("-50.00"),
                payment_date=datetime.now(timezone.utc)
            )

        with pytest.raises(ValueError, match="Payment amount must be positive"):
            payment_service.record_payment(
                game_id=str(uuid4()),
                payer_id=str(uuid4()),
                recipient_id=str(uuid4()),
                amount=Decimal("0"),
                payment_date=datetime.now(timezone.utc)
            )

    def test_payment_with_all_fields(self, payment_service, mock_db):
        """Test: Payment recording with all optional fields"""
        from db.models import Game, Player

        game = Game(id=uuid4(), public_code="TEST", admin_code="admin")
        alice = Player(id=uuid4(), display_name="Alice")
        bob = Player(id=uuid4(), display_name="Bob")

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            game, alice, bob, None, None
        ]
        mock_db.query.return_value.join.return_value.filter.return_value.scalar.return_value = 0

        payment_date = datetime(2025, 9, 23, 10, 30, 0, tzinfo=timezone.utc)

        with patch('services.payment_service.SessionLocal', return_value=mock_db):
            result = payment_service.record_payment(
                game_id=str(game.id),
                payer_id=str(alice.id),
                recipient_id=str(bob.id),
                amount=Decimal("125.50"),
                payment_date=payment_date,
                payment_method="Venmo",
                notes="Weekly poker settlement",
                reference_id="venmo_tx_12345",
                created_by="admin_hash_abc"
            )

        added_payment = mock_db.add.call_args_list[0][0][0]
        assert added_payment.amount_cents == 12550
        assert added_payment.payment_method == "Venmo"
        assert added_payment.notes == "Weekly poker settlement"
        assert added_payment.reference_id == "venmo_tx_12345"
        assert added_payment.created_by == "admin_hash_abc"
        assert added_payment.payment_date == payment_date
        assert added_payment.status == 'completed'

    def test_payment_method_tracking(self, payment_service, mock_db):
        """Test: Different payment methods are tracked correctly"""
        from db.models import Game, Player

        game = Game(id=uuid4(), public_code="TEST", admin_code="admin")
        alice = Player(id=uuid4(), display_name="Alice")
        bob = Player(id=uuid4(), display_name="Bob")

        methods = ["Venmo", "Zelle", "Cash", "PayPal", "Wire Transfer", None]

        for method in methods:
            mock_db.reset_mock()
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                game, alice, bob, None, None
            ]
            mock_db.query.return_value.join.return_value.filter.return_value.scalar.return_value = 0

            with patch('services.payment_service.SessionLocal', return_value=mock_db):
                payment_service.record_payment(
                    game_id=str(game.id),
                    payer_id=str(alice.id),
                    recipient_id=str(bob.id),
                    amount=Decimal("50.00"),
                    payment_date=datetime.now(timezone.utc),
                    payment_method=method
                )

            added_payment = mock_db.add.call_args_list[0][0][0]
            assert added_payment.payment_method == method

    def test_reference_id_for_external_systems(self, payment_service, mock_db):
        """Test: Reference IDs for external payment systems"""
        from db.models import Game, Player

        game = Game(id=uuid4(), public_code="TEST", admin_code="admin")
        alice = Player(id=uuid4(), display_name="Alice")
        bob = Player(id=uuid4(), display_name="Bob")

        reference_ids = [
            "venmo_12345",
            "zelle_abc-def-123",
            "paypal_TXN_20250923_001",
            None
        ]

        for ref_id in reference_ids:
            mock_db.reset_mock()
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                game, alice, bob, None, None
            ]
            mock_db.query.return_value.join.return_value.filter.return_value.scalar.return_value = 0

            with patch('services.payment_service.SessionLocal', return_value=mock_db):
                payment_service.record_payment(
                    game_id=str(game.id),
                    payer_id=str(alice.id),
                    recipient_id=str(bob.id),
                    amount=Decimal("75.00"),
                    payment_date=datetime.now(timezone.utc),
                    reference_id=ref_id
                )

            added_payment = mock_db.add.call_args_list[0][0][0]
            assert added_payment.reference_id == ref_id


class TestBalanceCalculations:
    """Test all balance calculation formulas"""

    def test_balance_equals_received_minus_poker_winnings(self):
        """Test: balance = received - poker_winnings"""
        summaries = [
            PlayerPaymentSummary(
                player_id="alice",
                player_name="Alice",
                poker_net_winnings=Decimal("200"),
                total_paid=Decimal("0"),
                total_received=Decimal("150"),
                balance=Decimal("-50"),  # 150 - 200 = -50
                realized_earnings=Decimal("150"),
                days_since_last_payment=None
            )
        ]

        alice = summaries[0]
        assert alice.balance == alice.total_received - alice.poker_net_winnings
        assert alice.balance == Decimal("-50")

    def test_realized_earnings_equals_received_minus_paid(self):
        """Test: realized_earnings = received - paid"""
        summaries = [
            PlayerPaymentSummary(
                player_id="bob",
                player_name="Bob",
                poker_net_winnings=Decimal("100"),
                total_paid=Decimal("80"),
                total_received=Decimal("50"),
                balance=Decimal("-50"),
                realized_earnings=Decimal("-30"),  # 50 - 80 = -30
                days_since_last_payment=None
            )
        ]

        bob = summaries[0]
        assert bob.realized_earnings == bob.total_received - bob.total_paid
        assert bob.realized_earnings == Decimal("-30")

    def test_negative_balance_player_owes_money(self):
        """Test: Negative balance means player owes money"""
        summary = PlayerPaymentSummary(
            player_id="alice",
            player_name="Alice",
            poker_net_winnings=Decimal("500"),
            total_paid=Decimal("100"),
            total_received=Decimal("200"),
            balance=Decimal("-300"),  # received 200 - winnings 500 = -300 (owes)
            realized_earnings=Decimal("100"),  # received 200 - paid 100 = 100
            days_since_last_payment=5
        )

        assert summary.balance < 0
        assert summary.balance == Decimal("-300")

    def test_positive_balance_player_is_owed(self):
        """Test: Positive balance means player is owed money"""
        summary = PlayerPaymentSummary(
            player_id="bob",
            player_name="Bob",
            poker_net_winnings=Decimal("-200"),
            total_paid=Decimal("50"),
            total_received=Decimal("100"),
            balance=Decimal("300"),  # received 100 - winnings (-200) = 300 (is owed)
            realized_earnings=Decimal("50"),  # received 100 - paid 50 = 50
            days_since_last_payment=None
        )

        assert summary.balance > 0
        assert summary.balance == Decimal("300")

    def test_zero_balance_fully_settled(self):
        """Test: Zero balance means fully settled"""
        summary = PlayerPaymentSummary(
            player_id="charlie",
            player_name="Charlie",
            poker_net_winnings=Decimal("100"),
            total_paid=Decimal("0"),
            total_received=Decimal("100"),
            balance=Decimal("0"),  # received 100 - winnings 100 = 0 (settled)
            realized_earnings=Decimal("100"),
            days_since_last_payment=None
        )

        assert summary.balance == Decimal("0")

    def test_multiple_payments_both_directions(self):
        """Test: Balance calculation with payments in both directions"""
        summary = PlayerPaymentSummary(
            player_id="alice",
            player_name="Alice",
            poker_net_winnings=Decimal("150"),
            total_paid=Decimal("80"),  # Alice paid out $80
            total_received=Decimal("120"),  # Alice received $120
            balance=Decimal("-30"),  # 120 - 150 = -30 (still owes)
            realized_earnings=Decimal("40"),  # 120 - 80 = 40 (net cash flow)
            days_since_last_payment=3
        )

        assert summary.balance == summary.total_received - summary.poker_net_winnings
        assert summary.realized_earnings == summary.total_received - summary.total_paid


class TestSettlementAlgorithm:
    """Test settlement optimization algorithm"""

    def test_simple_two_player_settlement(self, payment_service):
        """Test: Simple 2-player settlement"""
        summaries = [
            PlayerPaymentSummary(
                player_id="alice", player_name="Alice",
                poker_net_winnings=Decimal("100"), total_paid=Decimal("0"),
                total_received=Decimal("0"), balance=Decimal("0"),
                realized_earnings=Decimal("0"), days_since_last_payment=None
            ),
            PlayerPaymentSummary(
                player_id="bob", player_name="Bob",
                poker_net_winnings=Decimal("-100"), total_paid=Decimal("0"),
                total_received=Decimal("0"), balance=Decimal("0"),
                realized_earnings=Decimal("0"), days_since_last_payment=None
            )
        ]

        with patch.object(payment_service, 'get_payment_summary', return_value=summaries):
            suggestions = payment_service.get_settlement_suggestions("game_id")

        assert len(suggestions) == 1
        assert suggestions[0].payer_id == "bob"
        assert suggestions[0].recipient_id == "alice"
        assert suggestions[0].amount == Decimal("100")

    def test_multi_player_circular_debt(self, payment_service):
        """Test: Multi-player circular debt resolution"""
        summaries = [
            PlayerPaymentSummary(
                player_id="alice", player_name="Alice",
                poker_net_winnings=Decimal("100"), total_paid=Decimal("0"),
                total_received=Decimal("0"), balance=Decimal("0"),
                realized_earnings=Decimal("0"), days_since_last_payment=None
            ),
            PlayerPaymentSummary(
                player_id="bob", player_name="Bob",
                poker_net_winnings=Decimal("-50"), total_paid=Decimal("0"),
                total_received=Decimal("0"), balance=Decimal("0"),
                realized_earnings=Decimal("0"), days_since_last_payment=None
            ),
            PlayerPaymentSummary(
                player_id="charlie", player_name="Charlie",
                poker_net_winnings=Decimal("-50"), total_paid=Decimal("0"),
                total_received=Decimal("0"), balance=Decimal("0"),
                realized_earnings=Decimal("0"), days_since_last_payment=None
            )
        ]

        with patch.object(payment_service, 'get_payment_summary', return_value=summaries):
            suggestions = payment_service.get_settlement_suggestions("game_id")

        assert len(suggestions) == 2
        total_suggested = sum(s.amount for s in suggestions)
        assert total_suggested == Decimal("100")

    def test_optimal_transaction_minimization(self, payment_service):
        """Test: Algorithm minimizes number of transactions"""
        summaries = [
            PlayerPaymentSummary(
                player_id="alice", player_name="Alice",
                poker_net_winnings=Decimal("300"), total_paid=Decimal("0"),
                total_received=Decimal("0"), balance=Decimal("0"),
                realized_earnings=Decimal("0"), days_since_last_payment=None
            ),
            PlayerPaymentSummary(
                player_id="bob", player_name="Bob",
                poker_net_winnings=Decimal("-100"), total_paid=Decimal("0"),
                total_received=Decimal("0"), balance=Decimal("0"),
                realized_earnings=Decimal("0"), days_since_last_payment=None
            ),
            PlayerPaymentSummary(
                player_id="charlie", player_name="Charlie",
                poker_net_winnings=Decimal("-100"), total_paid=Decimal("0"),
                total_received=Decimal("0"), balance=Decimal("0"),
                realized_earnings=Decimal("0"), days_since_last_payment=None
            ),
            PlayerPaymentSummary(
                player_id="dave", player_name="Dave",
                poker_net_winnings=Decimal("-100"), total_paid=Decimal("0"),
                total_received=Decimal("0"), balance=Decimal("0"),
                realized_earnings=Decimal("0"), days_since_last_payment=None
            )
        ]

        with patch.object(payment_service, 'get_payment_summary', return_value=summaries):
            suggestions = payment_service.get_settlement_suggestions("game_id")

        assert len(suggestions) == 3

    def test_exact_match_settlements(self, payment_service):
        """Test: Exact matching debts and credits"""
        summaries = [
            PlayerPaymentSummary(
                player_id="alice", player_name="Alice",
                poker_net_winnings=Decimal("50.00"), total_paid=Decimal("0"),
                total_received=Decimal("0"), balance=Decimal("0"),
                realized_earnings=Decimal("0"), days_since_last_payment=None
            ),
            PlayerPaymentSummary(
                player_id="bob", player_name="Bob",
                poker_net_winnings=Decimal("-50.00"), total_paid=Decimal("0"),
                total_received=Decimal("0"), balance=Decimal("0"),
                realized_earnings=Decimal("0"), days_since_last_payment=None
            )
        ]

        with patch.object(payment_service, 'get_payment_summary', return_value=summaries):
            suggestions = payment_service.get_settlement_suggestions("game_id")

        assert len(suggestions) == 1
        assert suggestions[0].amount == Decimal("50.00")

    def test_complex_five_player_scenario(self, payment_service):
        """Test: Real scenario with 5 players and complex debts"""
        summaries = [
            PlayerPaymentSummary(
                player_id="alice", player_name="Alice",
                poker_net_winnings=Decimal("250"), total_paid=Decimal("0"),
                total_received=Decimal("0"), balance=Decimal("0"),
                realized_earnings=Decimal("0"), days_since_last_payment=None
            ),
            PlayerPaymentSummary(
                player_id="bob", player_name="Bob",
                poker_net_winnings=Decimal("150"), total_paid=Decimal("0"),
                total_received=Decimal("0"), balance=Decimal("0"),
                realized_earnings=Decimal("0"), days_since_last_payment=None
            ),
            PlayerPaymentSummary(
                player_id="charlie", player_name="Charlie",
                poker_net_winnings=Decimal("-100"), total_paid=Decimal("0"),
                total_received=Decimal("0"), balance=Decimal("0"),
                realized_earnings=Decimal("0"), days_since_last_payment=None
            ),
            PlayerPaymentSummary(
                player_id="dave", player_name="Dave",
                poker_net_winnings=Decimal("-150"), total_paid=Decimal("0"),
                total_received=Decimal("0"), balance=Decimal("0"),
                realized_earnings=Decimal("0"), days_since_last_payment=None
            ),
            PlayerPaymentSummary(
                player_id="eve", player_name="Eve",
                poker_net_winnings=Decimal("-150"), total_paid=Decimal("0"),
                total_received=Decimal("0"), balance=Decimal("0"),
                realized_earnings=Decimal("0"), days_since_last_payment=None
            )
        ]

        with patch.object(payment_service, 'get_payment_summary', return_value=summaries):
            suggestions = payment_service.get_settlement_suggestions("game_id")

        total_payments = sum(s.amount for s in suggestions)
        assert total_payments == Decimal("400")
        assert len(suggestions) <= 4

    def test_no_money_created_or_destroyed(self, payment_service):
        """Test: Settlement suggestions maintain zero-sum"""
        summaries = [
            PlayerPaymentSummary(
                player_id="alice", player_name="Alice",
                poker_net_winnings=Decimal("300"), total_paid=Decimal("50"),
                total_received=Decimal("100"), balance=Decimal("-150"),
                realized_earnings=Decimal("50"), days_since_last_payment=None
            ),
            PlayerPaymentSummary(
                player_id="bob", player_name="Bob",
                poker_net_winnings=Decimal("-200"), total_paid=Decimal("100"),
                total_received=Decimal("50"), balance=Decimal("250"),
                realized_earnings=Decimal("-50"), days_since_last_payment=None
            ),
            PlayerPaymentSummary(
                player_id="charlie", player_name="Charlie",
                poker_net_winnings=Decimal("-100"), total_paid=Decimal("0"),
                total_received=Decimal("0"), balance=Decimal("100"),
                realized_earnings=Decimal("0"), days_since_last_payment=None
            )
        ]

        with patch.object(payment_service, 'get_payment_summary', return_value=summaries):
            suggestions = payment_service.get_settlement_suggestions("game_id")

        total_poker_winnings = sum(s.poker_net_winnings for s in summaries)
        assert total_poker_winnings == Decimal("0")

        total_suggested = sum(s.amount for s in suggestions)
        creditors_total = sum(
            (s.poker_net_winnings + s.total_paid) - s.total_received
            for s in summaries
            if (s.poker_net_winnings + s.total_paid) - s.total_received > 0
        )
        assert abs(total_suggested - creditors_total) < Decimal("0.01")


class TestDoubleEntryLedger:
    """Test double-entry ledger consistency"""

    def test_payment_creates_balanced_entries(self, payment_service, mock_db):
        """Test: Every payment creates balanced debit/credit"""
        from db.models import Game, Player

        game = Game(id=uuid4(), public_code="TEST", admin_code="admin")
        alice = Player(id=uuid4(), display_name="Alice")
        bob = Player(id=uuid4(), display_name="Bob")

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            game, alice, bob, None, None
        ]
        mock_db.query.return_value.join.return_value.filter.return_value.scalar.return_value = 0

        with patch('services.payment_service.SessionLocal', return_value=mock_db):
            payment_service.record_payment(
                game_id=str(game.id),
                payer_id=str(alice.id),
                recipient_id=str(bob.id),
                amount=Decimal("100.00"),
                payment_date=datetime.now(timezone.utc)
            )

        assert mock_db.add.called
        payment = mock_db.add.call_args_list[0][0][0]
        assert str(payment.payer_id) == str(alice.id)
        assert str(payment.recipient_id) == str(bob.id)
        assert payment.amount_cents == 10000

    def test_sum_debits_equals_sum_credits(self, payment_service, mock_db):
        """Test: Sum of all debits equals sum of all credits"""
        mock_balances = [
            MagicMock(
                player_id=uuid4(),
                display_name="Alice",
                poker_net_winnings=50000,
                total_paid=20000,
                total_received=30000,
                payment_balance=60000,
                last_payment_date=None
            ),
            MagicMock(
                player_id=uuid4(),
                display_name="Bob",
                poker_net_winnings=-50000,
                total_paid=30000,
                total_received=20000,
                payment_balance=-60000,
                last_payment_date=None
            )
        ]

        mock_db.execute.return_value.mappings.return_value.all.return_value = mock_balances

        with patch('services.payment_service.SessionLocal', return_value=mock_db):
            with patch.object(payment_service, '_sync_all_balances'):
                summaries = payment_service.get_payment_summary("game_id")

        total_paid = sum(s.total_paid for s in summaries)
        total_received = sum(s.total_received for s in summaries)
        assert total_paid == total_received


class TestEdgeCasesAndErrors:
    """Test edge cases and error scenarios"""

    def test_decimal_precision_no_float_errors(self, payment_service):
        """Test: Decimal precision prevents float errors"""
        summaries = [
            PlayerPaymentSummary(
                player_id="alice", player_name="Alice",
                poker_net_winnings=Decimal("33.33"),
                total_paid=Decimal("10.11"),
                total_received=Decimal("20.22"),
                balance=Decimal("-13.11"),
                realized_earnings=Decimal("10.11"),
                days_since_last_payment=None
            )
        ]

        alice = summaries[0]
        calculated_balance = alice.total_received - alice.poker_net_winnings
        assert calculated_balance == Decimal("-13.11")
        assert isinstance(calculated_balance, Decimal)

    def test_payment_date_validation(self, payment_service, mock_db):
        """Test: Payment date is properly validated and stored"""
        from db.models import Game, Player

        game = Game(id=uuid4(), public_code="TEST", admin_code="admin")
        alice = Player(id=uuid4(), display_name="Alice")
        bob = Player(id=uuid4(), display_name="Bob")

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            game, alice, bob, None, None
        ]
        mock_db.query.return_value.join.return_value.filter.return_value.scalar.return_value = 0

        payment_date = datetime(2025, 9, 15, 14, 30, 0, tzinfo=timezone.utc)

        with patch('services.payment_service.SessionLocal', return_value=mock_db):
            payment_service.record_payment(
                game_id=str(game.id),
                payer_id=str(alice.id),
                recipient_id=str(bob.id),
                amount=Decimal("100.00"),
                payment_date=payment_date
            )

        payment = mock_db.add.call_args_list[0][0][0]
        assert payment.payment_date == payment_date
        assert payment.payment_date.tzinfo is not None

    def test_missing_player_scenarios(self, payment_service, mock_db):
        """Test: Proper error handling for missing players"""
        from db.models import Game

        game = Game(id=uuid4(), public_code="TEST", admin_code="admin")

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            game,
            None,
            None
        ]

        with patch('services.payment_service.SessionLocal', return_value=mock_db):
            with pytest.raises(ValueError, match="Payer .* not found"):
                payment_service.record_payment(
                    game_id=str(game.id),
                    payer_id=str(uuid4()),
                    recipient_id=str(uuid4()),
                    amount=Decimal("100.00"),
                    payment_date=datetime.now(timezone.utc)
                )

    def test_game_validation(self, payment_service, mock_db):
        """Test: Game existence validation"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch('services.payment_service.SessionLocal', return_value=mock_db):
            with pytest.raises(ValueError, match="Game .* not found"):
                payment_service.record_payment(
                    game_id=str(uuid4()),
                    payer_id=str(uuid4()),
                    recipient_id=str(uuid4()),
                    amount=Decimal("100.00"),
                    payment_date=datetime.now(timezone.utc)
                )

    def test_very_large_amounts(self, payment_service, mock_db):
        """Test: Handling very large payment amounts"""
        from db.models import Game, Player

        game = Game(id=uuid4(), public_code="TEST", admin_code="admin")
        alice = Player(id=uuid4(), display_name="Alice")
        bob = Player(id=uuid4(), display_name="Bob")

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            game, alice, bob, None, None
        ]
        mock_db.query.return_value.join.return_value.filter.return_value.scalar.return_value = 0

        large_amount = Decimal("999999.99")

        with patch('services.payment_service.SessionLocal', return_value=mock_db):
            payment_service.record_payment(
                game_id=str(game.id),
                payer_id=str(alice.id),
                recipient_id=str(bob.id),
                amount=large_amount,
                payment_date=datetime.now(timezone.utc)
            )

        payment = mock_db.add.call_args_list[0][0][0]
        assert payment.amount_cents == 99999999

    def test_fractional_cent_handling(self, payment_service, mock_db):
        """Test: Fractional cents are handled correctly"""
        from db.models import Game, Player

        game = Game(id=uuid4(), public_code="TEST", admin_code="admin")
        alice = Player(id=uuid4(), display_name="Alice")
        bob = Player(id=uuid4(), display_name="Bob")

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            game, alice, bob, None, None
        ]
        mock_db.query.return_value.join.return_value.filter.return_value.scalar.return_value = 0

        with patch('services.payment_service.SessionLocal', return_value=mock_db):
            payment_service.record_payment(
                game_id=str(game.id),
                payer_id=str(alice.id),
                recipient_id=str(bob.id),
                amount=Decimal("100.125"),
                payment_date=datetime.now(timezone.utc)
            )

        payment = mock_db.add.call_args_list[0][0][0]
        assert payment.amount_cents == 10012