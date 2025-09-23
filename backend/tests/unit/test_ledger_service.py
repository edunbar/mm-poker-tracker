import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from services.ledger_service import (
    get_all_session_summaries,
    update_session_summary,
    delete_session_summary,
    delete_entire_session,
    get_session_summary
)
from db.models import SessionPlayerSummary, Session, Player, Game, PaymentBalance


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
        admin_code="admin-secret"
    )


@pytest.fixture
def sample_session(sample_game):
    return Session(
        id=uuid4(),
        game_id=sample_game.id,
        external_id="pokernow_abc123",
        game_number=5,
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_player():
    return Player(
        id=uuid4(),
        display_name="Alice",
        external_id="alice@pokernow"
    )


@pytest.fixture
def sample_summary(sample_session, sample_player):
    return SessionPlayerSummary(
        session_id=sample_session.id,
        player_id=sample_player.id,
        buy_in_sum=10000,
        cash_out_sum=15000,
        in_game=0,
        net=5000,
        names=["Alice"]
    )


class TestGetAllSessionSummaries:

    def test_get_all_session_summaries_success(self, mock_db, sample_game, sample_session, sample_player, sample_summary):
        sample_summary.session = sample_session
        sample_summary.player = sample_player
        sample_session.game = sample_game

        mock_db.query.return_value.join.return_value.join.return_value.join.return_value.filter.return_value.options.return_value.order_by.return_value.all.return_value = [
            sample_summary
        ]

        with patch('services.ledger_service.SessionLocal', return_value=mock_db):
            result = get_all_session_summaries("TEST123")

        assert result['total_count'] == 1
        assert len(result['summaries']) == 1

        summary = result['summaries'][0]
        assert summary['player_name'] == "Alice"
        assert summary['buy_in_sum'] == 10000
        assert summary['cash_out_sum'] == 15000
        assert summary['net'] == 5000
        assert summary['game_number'] == 5

    def test_get_all_session_summaries_empty_game(self, mock_db):
        mock_db.query.return_value.join.return_value.join.return_value.join.return_value.filter.return_value.options.return_value.order_by.return_value.all.return_value = []

        with patch('services.ledger_service.SessionLocal', return_value=mock_db):
            result = get_all_session_summaries("EMPTY123")

        assert result['total_count'] == 0
        assert result['summaries'] == []

    def test_get_all_session_summaries_ordered_by_game_number_desc(self, mock_db, sample_game):
        session1 = Session(id=uuid4(), game_id=sample_game.id, game_number=1, external_id="session1")
        session2 = Session(id=uuid4(), game_id=sample_game.id, game_number=5, external_id="session2")
        player = Player(id=uuid4(), display_name="Bob")

        summary1 = SessionPlayerSummary(session_id=session1.id, player_id=player.id, buy_in_sum=1000, cash_out_sum=2000, in_game=0, net=1000, names=["Bob"])
        summary2 = SessionPlayerSummary(session_id=session2.id, player_id=player.id, buy_in_sum=3000, cash_out_sum=4000, in_game=0, net=1000, names=["Bob"])

        summary1.session = session1
        summary1.player = player
        summary2.session = session2
        summary2.player = player
        session1.game = sample_game
        session2.game = sample_game

        mock_db.query.return_value.join.return_value.join.return_value.join.return_value.filter.return_value.options.return_value.order_by.return_value.all.return_value = [
            summary2, summary1
        ]

        with patch('services.ledger_service.SessionLocal', return_value=mock_db):
            result = get_all_session_summaries("TEST123")

        assert result['summaries'][0]['game_number'] == 5
        assert result['summaries'][1]['game_number'] == 1


class TestUpdateSessionSummary:

    def test_update_session_summary_success(self, mock_db, sample_summary):
        mock_db.query.return_value.filter.return_value.first.return_value = sample_summary

        updates = {
            'buy_in_sum': 20000,
            'cash_out_sum': 25000
        }

        with patch('services.ledger_service.SessionLocal', return_value=mock_db):
            with patch('services.ledger_service.audit_context'):
                result = update_session_summary(
                    str(sample_summary.session_id),
                    str(sample_summary.player_id),
                    updates
                )

        assert result['message'] == "SessionPlayerSummary updated successfully"
        assert sample_summary.buy_in_sum == 20000
        assert sample_summary.cash_out_sum == 25000
        mock_db.commit.assert_called_once()

    def test_update_session_summary_not_found(self, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch('services.ledger_service.SessionLocal', return_value=mock_db):
            with patch('services.ledger_service.audit_context'):
                with pytest.raises(ValueError, match="SessionPlayerSummary not found"):
                    update_session_summary(str(uuid4()), str(uuid4()), {'buy_in_sum': 1000})

    def test_update_session_summary_validates_names_field(self, mock_db, sample_summary):
        mock_db.query.return_value.filter.return_value.first.return_value = sample_summary

        updates = {'names': "not a list"}

        with patch('services.ledger_service.SessionLocal', return_value=mock_db):
            with patch('services.ledger_service.audit_context'):
                with pytest.raises(ValueError, match="Field 'names' must be a list"):
                    update_session_summary(
                        str(sample_summary.session_id),
                        str(sample_summary.player_id),
                        updates
                    )

    def test_update_session_summary_ignores_game_number(self, mock_db, sample_summary):
        original_buy_in = sample_summary.buy_in_sum
        mock_db.query.return_value.filter.return_value.first.return_value = sample_summary

        updates = {
            'game_number': 999,
            'buy_in_sum': 30000
        }

        with patch('services.ledger_service.SessionLocal', return_value=mock_db):
            with patch('services.ledger_service.audit_context'):
                result = update_session_summary(
                    str(sample_summary.session_id),
                    str(sample_summary.player_id),
                    updates
                )

        assert sample_summary.buy_in_sum == 30000
        assert len(result['updated_fields']) == 1
        assert result['updated_fields'][0]['field'] == 'buy_in_sum'

    def test_update_session_summary_no_valid_fields(self, mock_db, sample_summary):
        mock_db.query.return_value.filter.return_value.first.return_value = sample_summary

        updates = {'invalid_field': 123}

        with patch('services.ledger_service.SessionLocal', return_value=mock_db):
            with patch('services.ledger_service.audit_context'):
                result = update_session_summary(
                    str(sample_summary.session_id),
                    str(sample_summary.player_id),
                    updates
                )

        assert result['message'] == "No valid fields to update"
        assert result['updated_fields'] == []


class TestDeleteSessionSummary:

    def test_delete_session_summary_updates_payment_balances(self, mock_db, sample_summary, sample_session, sample_game):
        sample_session.game_id = sample_game.id
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_summary,
            sample_session,
            sample_game
        ]
        mock_db.query.return_value.filter.return_value.count.return_value = 1
        mock_db.query.return_value.join.return_value.filter.return_value.count.return_value = 0

        with patch('services.ledger_service.SessionLocal', return_value=mock_db):
            with patch('services.ledger_service.audit_context'):
                with patch('services.payment_service.PaymentService') as MockPaymentService:
                    mock_payment_service = MockPaymentService.return_value
                    delete_session_summary(
                        str(sample_summary.session_id),
                        str(sample_summary.player_id)
                    )

                    mock_payment_service._update_payment_balances.assert_called_once_with(
                        mock_db,
                        str(sample_game.id),
                        [str(sample_summary.player_id)]
                    )

    def test_delete_session_summary_removes_payment_balance_if_no_activity(self, mock_db, sample_summary, sample_session, sample_game):
        sample_session.game_id = sample_game.id
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_summary,
            sample_session,
            sample_game
        ]
        mock_db.query.return_value.filter.return_value.count.return_value = 1
        mock_db.query.return_value.join.return_value.filter.return_value.count.return_value = 0

        with patch('services.ledger_service.SessionLocal', return_value=mock_db):
            with patch('services.ledger_service.audit_context'):
                with patch('services.payment_service.PaymentService'):
                    delete_session_summary(
                        str(sample_summary.session_id),
                        str(sample_summary.player_id)
                    )

        delete_query = mock_db.query.return_value.filter.return_value.delete
        delete_query.assert_called()

    def test_delete_session_summary_not_found(self, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch('services.ledger_service.SessionLocal', return_value=mock_db):
            with patch('services.ledger_service.audit_context'):
                with pytest.raises(ValueError, match="SessionPlayerSummary not found"):
                    delete_session_summary(str(uuid4()), str(uuid4()))


class TestDeleteEntireSession:

    def test_delete_entire_session_success(self, mock_db, sample_session, sample_summary, sample_player):
        sample_summary.player = sample_player
        mock_db.query.return_value.filter.return_value.first.side_effect = [sample_session, None]
        mock_db.query.return_value.filter.return_value.all.return_value = [sample_summary]
        mock_db.query.return_value.join.return_value.filter.return_value.count.return_value = 0

        with patch('services.ledger_service.SessionLocal', return_value=mock_db):
            with patch('services.ledger_service.audit_context'):
                with patch('services.payment_service.PaymentService'):
                    result = delete_entire_session(str(sample_session.id))

        assert result['message'] == "Entire session deleted successfully"
        assert result['total_players_deleted'] == 1
        assert result['deleted_session']['external_id'] == "pokernow_abc123"
        mock_db.delete.assert_called_once_with(sample_session)

    def test_delete_entire_session_not_found(self, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch('services.ledger_service.SessionLocal', return_value=mock_db):
            with patch('services.ledger_service.audit_context'):
                with pytest.raises(ValueError, match="Session not found"):
                    delete_entire_session(str(uuid4()))

    def test_delete_entire_session_updates_all_player_balances(self, mock_db, sample_session, sample_game):
        player1 = Player(id=uuid4(), display_name="Alice")
        player2 = Player(id=uuid4(), display_name="Bob")

        summary1 = SessionPlayerSummary(session_id=sample_session.id, player_id=player1.id, buy_in_sum=1000, cash_out_sum=2000, in_game=0, net=1000, names=["Alice"])
        summary2 = SessionPlayerSummary(session_id=sample_session.id, player_id=player2.id, buy_in_sum=2000, cash_out_sum=1000, in_game=0, net=-1000, names=["Bob"])

        summary1.player = player1
        summary2.player = player2
        sample_session.game_id = sample_game.id

        mock_db.query.return_value.filter.return_value.first.side_effect = [sample_session, sample_game]
        mock_db.query.return_value.filter.return_value.all.return_value = [summary1, summary2]
        mock_db.query.return_value.join.return_value.filter.return_value.count.return_value = 0

        with patch('services.ledger_service.SessionLocal', return_value=mock_db):
            with patch('services.ledger_service.audit_context'):
                with patch('services.payment_service.PaymentService') as MockPaymentService:
                    mock_payment_service = MockPaymentService.return_value
                    delete_entire_session(str(sample_session.id))

                    mock_payment_service._update_payment_balances.assert_called_once_with(
                        mock_db,
                        str(sample_game.id),
                        [str(player1.id), str(player2.id)]
                    )


class TestGetSessionSummary:

    def test_get_session_summary_success(self, mock_db, sample_summary, sample_session, sample_player):
        sample_summary.session = sample_session
        sample_summary.player = sample_player

        mock_db.query.return_value.join.return_value.join.return_value.filter.return_value.options.return_value.first.return_value = sample_summary

        with patch('services.ledger_service.SessionLocal', return_value=mock_db):
            result = get_session_summary(
                str(sample_summary.session_id),
                str(sample_summary.player_id)
            )

        assert result['player_name'] == "Alice"
        assert result['buy_in_sum'] == 10000
        assert result['cash_out_sum'] == 15000
        assert result['net'] == 5000

    def test_get_session_summary_not_found(self, mock_db):
        mock_db.query.return_value.join.return_value.join.return_value.filter.return_value.options.return_value.first.return_value = None

        with patch('services.ledger_service.SessionLocal', return_value=mock_db):
            with pytest.raises(ValueError, match="SessionPlayerSummary not found"):
                get_session_summary(str(uuid4()), str(uuid4()))


class TestEdgeCases:

    def test_delete_entire_session_invalidates_cache(self, mock_db, sample_session, sample_game):
        sample_session.game_id = sample_game.id
        mock_db.query.return_value.filter.return_value.first.side_effect = [sample_session, sample_game]
        mock_db.query.return_value.filter.return_value.all.return_value = []

        with patch('services.ledger_service.SessionLocal', return_value=mock_db):
            with patch('services.ledger_service.audit_context'):
                with patch('services.payment_service.PaymentService'):
                    with patch('services.game_summary_service.invalidate_game_cache') as mock_invalidate:
                        delete_entire_session(str(sample_session.id))
                        mock_invalidate.assert_called_once_with(sample_game.public_code)