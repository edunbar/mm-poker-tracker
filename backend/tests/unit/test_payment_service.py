import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch, call
from uuid import uuid4

from services.payment_service import PaymentService, PlayerPaymentSummary, SettlementSuggestion
from db.models import Game, Player, PaymentTransaction, PaymentBalance, SessionPlayerSummary, Session


@pytest.fixture
def payment_service():
    return PaymentService()


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.__enter__ = Mock(return_value=db)
    db.__exit__ = Mock(return_value=None)
    return db


@pytest.fixture
def sample_game():
    return Game(
        id=uuid4(),
        public_code="TEST123",
        admin_code="admin-secret-123",
        title="Test Game"
    )


@pytest.fixture
def sample_players():
    return [
        Player(id=uuid4(), display_name="Alice", external_id="alice@pokernow"),
        Player(id=uuid4(), display_name="Bob", external_id="bob@pokernow"),
        Player(id=uuid4(), display_name="Charlie", external_id="charlie@pokernow")
    ]


class TestRecordPayment:

    def test_record_payment_success(self, payment_service, mock_db, sample_game, sample_players):
        alice, bob, _ = sample_players

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_game,
            alice,
            bob,
            None,
            None
        ]

        mock_db.query.return_value.join.return_value.filter.return_value.scalar.return_value = 0

        with patch('services.payment_service.SessionLocal', return_value=mock_db):
            result = payment_service.record_payment(
                game_id=str(sample_game.id),
                payer_id=str(alice.id),
                recipient_id=str(bob.id),
                amount=Decimal("100.00"),
                payment_date=datetime.now(timezone.utc),
                payment_method="Venmo",
                notes="Test payment",
                reference_id="venmo_123"
            )

        mock_db.add.assert_called()
        mock_db.flush.assert_called()
        mock_db.commit.assert_called_once()

        added_payment = mock_db.add.call_args_list[0][0][0]
        assert isinstance(added_payment, PaymentTransaction)
        assert added_payment.amount_cents == 10000
        assert added_payment.payment_method == "Venmo"
        assert added_payment.notes == "Test payment"

    def test_record_payment_same_payer_recipient_fails(self, payment_service):
        game_id = str(uuid4())
        player_id = str(uuid4())

        with pytest.raises(ValueError, match="Payer and recipient cannot be the same"):
            payment_service.record_payment(
                game_id=game_id,
                payer_id=player_id,
                recipient_id=player_id,
                amount=Decimal("100.00"),
                payment_date=datetime.now(timezone.utc)
            )

    def test_record_payment_negative_amount_fails(self, payment_service):
        with pytest.raises(ValueError, match="Payment amount must be positive"):
            payment_service.record_payment(
                game_id=str(uuid4()),
                payer_id=str(uuid4()),
                recipient_id=str(uuid4()),
                amount=Decimal("-50.00"),
                payment_date=datetime.now(timezone.utc)
            )

    def test_record_payment_zero_amount_fails(self, payment_service):
        with pytest.raises(ValueError, match="Payment amount must be positive"):
            payment_service.record_payment(
                game_id=str(uuid4()),
                payer_id=str(uuid4()),
                recipient_id=str(uuid4()),
                amount=Decimal("0"),
                payment_date=datetime.now(timezone.utc)
            )

    def test_record_payment_game_not_found(self, payment_service, mock_db):
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

    def test_record_payment_payer_not_found(self, payment_service, mock_db, sample_game):
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_game,
            None,
            None
        ]

        with patch('services.payment_service.SessionLocal', return_value=mock_db):
            with pytest.raises(ValueError, match="Payer .* not found"):
                payment_service.record_payment(
                    game_id=str(sample_game.id),
                    payer_id=str(uuid4()),
                    recipient_id=str(uuid4()),
                    amount=Decimal("100.00"),
                    payment_date=datetime.now(timezone.utc)
                )

    def test_record_payment_recipient_not_found(self, payment_service, mock_db, sample_game, sample_players):
        alice, _, _ = sample_players

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_game,
            alice,
            None
        ]

        with patch('services.payment_service.SessionLocal', return_value=mock_db):
            with pytest.raises(ValueError, match="Recipient .* not found"):
                payment_service.record_payment(
                    game_id=str(sample_game.id),
                    payer_id=str(alice.id),
                    recipient_id=str(uuid4()),
                    amount=Decimal("100.00"),
                    payment_date=datetime.now(timezone.utc)
                )


class TestGetPaymentSummary:

    def test_get_payment_summary_success(self, payment_service, mock_db, sample_game):
        mock_balance_result = [
            MagicMock(
                player_id=uuid4(),
                display_name="Alice",
                poker_net_winnings=50000,
                total_paid=20000,
                total_received=10000,
                payment_balance=-10000,
                last_payment_date=datetime.now(timezone.utc) - timedelta(days=5)
            ),
            MagicMock(
                player_id=uuid4(),
                display_name="Bob",
                poker_net_winnings=-30000,
                total_paid=0,
                total_received=15000,
                payment_balance=45000,
                last_payment_date=None
            )
        ]

        mock_db.execute.return_value.mappings.return_value.all.return_value = mock_balance_result

        with patch('services.payment_service.SessionLocal', return_value=mock_db):
            result = payment_service.get_payment_summary(str(sample_game.id))

        assert len(result) == 2
        assert all(isinstance(summary, PlayerPaymentSummary) for summary in result)

        bob_summary = result[0]
        assert bob_summary.player_name == "Bob"
        assert bob_summary.balance == Decimal("450.00")
        assert bob_summary.realized_earnings == Decimal("150.00")
        assert bob_summary.days_since_last_payment is None

        alice_summary = result[1]
        assert alice_summary.player_name == "Alice"
        assert alice_summary.balance == Decimal("-400.00")
        assert alice_summary.realized_earnings == Decimal("-100.00")
        assert alice_summary.days_since_last_payment == 5

    def test_get_payment_summary_empty_game(self, payment_service, mock_db, sample_game):
        mock_db.execute.return_value.mappings.return_value.all.return_value = []

        with patch('services.payment_service.SessionLocal', return_value=mock_db):
            result = payment_service.get_payment_summary(str(sample_game.id))

        assert result == []

    def test_get_payment_summary_syncs_balances_first(self, payment_service, mock_db, sample_game):
        mock_db.execute.return_value.mappings.return_value.all.return_value = []

        with patch('services.payment_service.SessionLocal', return_value=mock_db):
            with patch.object(payment_service, '_sync_all_balances') as mock_sync:
                payment_service.get_payment_summary(str(sample_game.id))
                mock_sync.assert_called_once_with(mock_db, str(sample_game.id))


class TestGetSettlementSuggestions:

    def test_settlement_suggestions_simple_case(self, payment_service):
        summaries = [
            PlayerPaymentSummary(
                player_id="alice",
                player_name="Alice",
                poker_net_winnings=Decimal("100"),
                total_paid=Decimal("0"),
                total_received=Decimal("0"),
                balance=Decimal("0"),
                realized_earnings=Decimal("0"),
                days_since_last_payment=None
            ),
            PlayerPaymentSummary(
                player_id="bob",
                player_name="Bob",
                poker_net_winnings=Decimal("-100"),
                total_paid=Decimal("0"),
                total_received=Decimal("0"),
                balance=Decimal("0"),
                realized_earnings=Decimal("0"),
                days_since_last_payment=None
            )
        ]

        with patch.object(payment_service, 'get_payment_summary', return_value=summaries):
            suggestions = payment_service.get_settlement_suggestions("game_id")

        assert len(suggestions) == 1
        assert suggestions[0].payer_id == "bob"
        assert suggestions[0].payer_name == "Bob"
        assert suggestions[0].recipient_id == "alice"
        assert suggestions[0].recipient_name == "Alice"
        assert suggestions[0].amount == Decimal("100")

    def test_settlement_suggestions_multi_player(self, payment_service):
        summaries = [
            PlayerPaymentSummary(
                player_id="alice",
                player_name="Alice",
                poker_net_winnings=Decimal("200"),
                total_paid=Decimal("0"),
                total_received=Decimal("0"),
                balance=Decimal("0"),
                realized_earnings=Decimal("0"),
                days_since_last_payment=None
            ),
            PlayerPaymentSummary(
                player_id="bob",
                player_name="Bob",
                poker_net_winnings=Decimal("-150"),
                total_paid=Decimal("0"),
                total_received=Decimal("0"),
                balance=Decimal("0"),
                realized_earnings=Decimal("0"),
                days_since_last_payment=None
            ),
            PlayerPaymentSummary(
                player_id="charlie",
                player_name="Charlie",
                poker_net_winnings=Decimal("-50"),
                total_paid=Decimal("0"),
                total_received=Decimal("0"),
                balance=Decimal("0"),
                realized_earnings=Decimal("0"),
                days_since_last_payment=None
            )
        ]

        with patch.object(payment_service, 'get_payment_summary', return_value=summaries):
            suggestions = payment_service.get_settlement_suggestions("game_id")

        assert len(suggestions) <= 2
        total_suggested = sum(s.amount for s in suggestions)
        assert total_suggested == Decimal("200")

    def test_settlement_suggestions_with_partial_payments(self, payment_service):
        summaries = [
            PlayerPaymentSummary(
                player_id="alice",
                player_name="Alice",
                poker_net_winnings=Decimal("100"),
                total_paid=Decimal("0"),
                total_received=Decimal("40"),
                balance=Decimal("-60"),
                realized_earnings=Decimal("40"),
                days_since_last_payment=None
            ),
            PlayerPaymentSummary(
                player_id="bob",
                player_name="Bob",
                poker_net_winnings=Decimal("-100"),
                total_paid=Decimal("40"),
                total_received=Decimal("0"),
                balance=Decimal("60"),
                realized_earnings=Decimal("-40"),
                days_since_last_payment=5
            )
        ]

        with patch.object(payment_service, 'get_payment_summary', return_value=summaries):
            suggestions = payment_service.get_settlement_suggestions("game_id")

        assert len(suggestions) == 1
        assert suggestions[0].amount == Decimal("60")

    def test_settlement_suggestions_ignores_small_amounts(self, payment_service):
        summaries = [
            PlayerPaymentSummary(
                player_id="alice",
                player_name="Alice",
                poker_net_winnings=Decimal("0.005"),
                total_paid=Decimal("0"),
                total_received=Decimal("0"),
                balance=Decimal("0"),
                realized_earnings=Decimal("0"),
                days_since_last_payment=None
            ),
            PlayerPaymentSummary(
                player_id="bob",
                player_name="Bob",
                poker_net_winnings=Decimal("-0.005"),
                total_paid=Decimal("0"),
                total_received=Decimal("0"),
                balance=Decimal("0"),
                realized_earnings=Decimal("0"),
                days_since_last_payment=None
            )
        ]

        with patch.object(payment_service, 'get_payment_summary', return_value=summaries):
            suggestions = payment_service.get_settlement_suggestions("game_id")

        assert len(suggestions) == 0

    def test_settlement_suggestions_already_settled(self, payment_service):
        summaries = [
            PlayerPaymentSummary(
                player_id="alice",
                player_name="Alice",
                poker_net_winnings=Decimal("100"),
                total_paid=Decimal("0"),
                total_received=Decimal("100"),
                balance=Decimal("0"),
                realized_earnings=Decimal("100"),
                days_since_last_payment=None
            ),
            PlayerPaymentSummary(
                player_id="bob",
                player_name="Bob",
                poker_net_winnings=Decimal("-100"),
                total_paid=Decimal("100"),
                total_received=Decimal("0"),
                balance=Decimal("0"),
                realized_earnings=Decimal("-100"),
                days_since_last_payment=1
            )
        ]

        with patch.object(payment_service, 'get_payment_summary', return_value=summaries):
            suggestions = payment_service.get_settlement_suggestions("game_id")

        assert len(suggestions) == 0


class TestGetPaymentHistory:

    def test_get_payment_history_success(self, payment_service, mock_db):
        payment1_id = uuid4()
        payment2_id = uuid4()

        mock_payments = [
            (
                MagicMock(
                    id=payment1_id,
                    amount_cents=10000,
                    payment_method="Venmo",
                    payment_date=datetime.now(timezone.utc),
                    status="completed",
                    notes="Payment 1",
                    reference_id="venmo_1",
                    created_at=datetime.now(timezone.utc)
                ),
                "Alice",
                "Bob"
            ),
            (
                MagicMock(
                    id=payment2_id,
                    amount_cents=5000,
                    payment_method="Zelle",
                    payment_date=datetime.now(timezone.utc) - timedelta(days=1),
                    status="completed",
                    notes="Payment 2",
                    reference_id="zelle_1",
                    created_at=datetime.now(timezone.utc) - timedelta(days=1)
                ),
                "Bob",
                "Charlie"
            )
        ]

        mock_db.query.return_value.join.return_value.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = mock_payments

        with patch('services.payment_service.SessionLocal', return_value=mock_db):
            result = payment_service.get_payment_history("game_id", limit=10, offset=0)

        assert len(result) == 2
        assert result[0]['id'] == str(payment1_id)
        assert result[0]['payer_name'] == "Alice"
        assert result[0]['recipient_name'] == "Bob"
        assert result[0]['amount'] == 100.0
        assert result[1]['amount'] == 50.0

    def test_get_payment_history_respects_pagination(self, payment_service, mock_db):
        mock_db.query.return_value.join.return_value.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = []

        with patch('services.payment_service.SessionLocal', return_value=mock_db):
            payment_service.get_payment_history("game_id", limit=50, offset=100)

        mock_db.query.return_value.join.return_value.filter.return_value.order_by.return_value.limit.assert_called_with(50)
        mock_db.query.return_value.join.return_value.filter.return_value.order_by.return_value.limit.return_value.offset.assert_called_with(100)


class TestUpdatePaymentBalances:

    def test_update_payment_balances_creates_new_balance(self, payment_service, mock_db):
        player_id = str(uuid4())
        game_id = str(uuid4())

        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.join.return_value.filter.return_value.scalar.return_value = 50000
        mock_db.query.return_value.filter.return_value.scalar.side_effect = [
            10000,
            5000
        ]

        payment_service._update_payment_balances(mock_db, game_id, [player_id])

        mock_db.add.assert_called_once()
        added_balance = mock_db.add.call_args[0][0]
        assert isinstance(added_balance, PaymentBalance)
        assert added_balance.poker_net_winnings == 50000
        assert added_balance.total_paid == 10000
        assert added_balance.total_received == 5000
        assert added_balance.payment_balance == 45000

    def test_update_payment_balances_updates_existing_balance(self, payment_service, mock_db):
        player_id = str(uuid4())
        game_id = str(uuid4())

        existing_balance = PaymentBalance(
            game_id=game_id,
            player_id=player_id,
            poker_net_winnings=0,
            total_paid=0,
            total_received=0,
            payment_balance=0
        )

        mock_db.query.return_value.filter.return_value.first.return_value = existing_balance
        mock_db.query.return_value.join.return_value.filter.return_value.scalar.return_value = 30000
        mock_db.query.return_value.filter.return_value.scalar.side_effect = [
            15000,
            20000
        ]

        payment_service._update_payment_balances(mock_db, game_id, [player_id])

        assert existing_balance.poker_net_winnings == 30000
        assert existing_balance.total_paid == 15000
        assert existing_balance.total_received == 20000
        assert existing_balance.payment_balance == 35000
        mock_db.flush.assert_called_once()

    def test_update_payment_balances_multiple_players(self, payment_service, mock_db):
        player_ids = [str(uuid4()), str(uuid4())]
        game_id = str(uuid4())

        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.join.return_value.filter.return_value.scalar.side_effect = [
            10000, 5000, 3000,
            20000, 8000, 6000
        ]

        payment_service._update_payment_balances(mock_db, game_id, player_ids)

        assert mock_db.add.call_count == 2
        assert mock_db.flush.call_count == 2


class TestSyncAllBalances:

    def test_sync_all_balances_includes_session_players(self, payment_service, mock_db):
        game_id = str(uuid4())
        player_id = str(uuid4())

        mock_session_players = MagicMock()
        mock_session_players.distinct.return_value.union.return_value.all.return_value = [(player_id,)]

        mock_db.query.return_value.join.return_value.filter.return_value = mock_session_players
        mock_db.query.return_value.filter.return_value.union.return_value = mock_session_players

        with patch.object(payment_service, '_update_payment_balances') as mock_update:
            payment_service._sync_all_balances(mock_db, game_id)
            mock_update.assert_called_once_with(mock_db, game_id, [player_id])

    def test_sync_all_balances_includes_payment_players(self, payment_service, mock_db):
        game_id = str(uuid4())
        player_id = str(uuid4())

        mock_union_query = MagicMock()
        mock_union_query.all.return_value = [(player_id,)]

        mock_db.query.return_value.join.return_value.filter.return_value.distinct.return_value.union.return_value = mock_union_query

        with patch.object(payment_service, '_update_payment_balances') as mock_update:
            payment_service._sync_all_balances(mock_db, game_id)
            mock_update.assert_called_once_with(mock_db, game_id, [player_id])


class TestEdgeCases:

    def test_payment_balance_calculation_with_zero_winnings(self, payment_service, mock_db):
        player_id = str(uuid4())
        game_id = str(uuid4())

        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.join.return_value.filter.return_value.scalar.return_value = 0
        mock_db.query.return_value.filter.return_value.scalar.side_effect = [
            0,
            0
        ]

        payment_service._update_payment_balances(mock_db, game_id, [player_id])

        added_balance = mock_db.add.call_args[0][0]
        assert added_balance.payment_balance == 0

    def test_payment_summary_handles_string_date(self, payment_service, mock_db, sample_game):
        mock_balance_result = [
            MagicMock(
                player_id=uuid4(),
                display_name="Alice",
                poker_net_winnings=10000,
                total_paid=0,
                total_received=0,
                payment_balance=-10000,
                last_payment_date="2025-09-18T10:30:00Z"
            )
        ]

        mock_db.execute.return_value.mappings.return_value.all.return_value = mock_balance_result

        with patch('services.payment_service.SessionLocal', return_value=mock_db):
            result = payment_service.get_payment_summary(str(sample_game.id))

        assert len(result) == 1
        assert result[0].days_since_last_payment is not None

    def test_settlement_with_precision_edge_case(self, payment_service):
        summaries = [
            PlayerPaymentSummary(
                player_id="alice",
                player_name="Alice",
                poker_net_winnings=Decimal("33.33"),
                total_paid=Decimal("0"),
                total_received=Decimal("0"),
                balance=Decimal("0"),
                realized_earnings=Decimal("0"),
                days_since_last_payment=None
            ),
            PlayerPaymentSummary(
                player_id="bob",
                player_name="Bob",
                poker_net_winnings=Decimal("-33.33"),
                total_paid=Decimal("0"),
                total_received=Decimal("0"),
                balance=Decimal("0"),
                realized_earnings=Decimal("0"),
                days_since_last_payment=None
            )
        ]

        with patch.object(payment_service, 'get_payment_summary', return_value=summaries):
            suggestions = payment_service.get_settlement_suggestions("game_id")

        assert len(suggestions) == 1
        assert suggestions[0].amount == Decimal("33.33")