import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from services.ledger_analysis_service import (
    get_ledger_analysis,
    get_session_detail,
    recalculate_session_balance,
    _get_overall_balance,
    _get_session_analysis,
    _get_player_anomalies,
    _identify_problems,
    _check_temporal_consistency,
    _detect_statistical_outliers,
    _validate_cross_session_data,
    _check_business_logic_violations,
    _check_payment_ledger_balance
)
from db.models import Game, Session as SessionModel, SessionPlayerSummary, Player


@pytest.fixture
def mock_db():
    db = MagicMock()
    return db


@pytest.fixture
def sample_game():
    return Game(
        id=uuid4(),
        public_code="TEST123",
        admin_code="admin-secret"
    )


class TestGetOverallBalance:

    def test_get_overall_balance_balanced_game(self, mock_db):
        game_id = str(uuid4())

        mock_result = MagicMock(
            total_buy_ins=100000,
            total_cash_outs=80000,
            total_in_game=20000,
            total_net=0,
            total_sessions=3,
            total_entries=9
        )

        mock_db.execute.return_value.fetchone.return_value = mock_result

        result = _get_overall_balance(mock_db, game_id)

        assert result['total_buy_ins'] == 100000
        assert result['total_cash_outs'] == 80000
        assert result['total_in_game'] == 20000
        assert result['effective_cash_outs'] == 100000
        assert result['balance'] == 0
        assert result['is_balanced'] is True
        assert result['imbalance_percentage'] == 0.0

    def test_get_overall_balance_imbalanced_game(self, mock_db):
        game_id = str(uuid4())

        mock_result = MagicMock(
            total_buy_ins=100000,
            total_cash_outs=90000,
            total_in_game=5000,
            total_net=0,
            total_sessions=2,
            total_entries=6
        )

        mock_db.execute.return_value.fetchone.return_value = mock_result

        result = _get_overall_balance(mock_db, game_id)

        assert result['balance'] == -5000
        assert result['is_balanced'] is False
        assert result['imbalance_percentage'] == 5.0

    def test_get_overall_balance_no_data(self, mock_db):
        game_id = str(uuid4())
        mock_db.execute.return_value.fetchone.return_value = None

        result = _get_overall_balance(mock_db, game_id)

        assert result['total_buy_ins'] == 0
        assert result['is_balanced'] is True
        assert result['balance'] == 0


class TestGetSessionAnalysis:

    def test_get_session_analysis_multiple_sessions(self, mock_db):
        game_id = str(uuid4())

        mock_results = [
            MagicMock(
                session_id=uuid4(),
                external_id="session1",
                game_number=2,
                started_at=datetime.now(timezone.utc),
                session_buy_ins=50000,
                session_cash_outs=40000,
                session_in_game=10000,
                session_net=0,
                player_count=3
            ),
            MagicMock(
                session_id=uuid4(),
                external_id="session2",
                game_number=1,
                started_at=datetime.now(timezone.utc),
                session_buy_ins=30000,
                session_cash_outs=30000,
                session_in_game=0,
                session_net=0,
                player_count=2
            )
        ]

        mock_db.execute.return_value.fetchall.return_value = mock_results

        result = _get_session_analysis(mock_db, game_id)

        assert len(result) == 2
        assert result[0]['game_number'] == 2
        assert result[0]['is_balanced'] is True
        assert result[0]['balance'] == 0
        assert result[1]['game_number'] == 1

    def test_get_session_analysis_unbalanced_session(self, mock_db):
        game_id = str(uuid4())

        mock_results = [
            MagicMock(
                session_id=uuid4(),
                external_id="bad_session",
                game_number=1,
                started_at=datetime.now(timezone.utc),
                session_buy_ins=50000,
                session_cash_outs=45000,
                session_in_game=0,
                session_net=0,
                player_count=3
            )
        ]

        mock_db.execute.return_value.fetchall.return_value = mock_results

        result = _get_session_analysis(mock_db, game_id)

        assert result[0]['is_balanced'] is False
        assert result[0]['balance'] == -5000

    def test_get_session_analysis_significant_in_game(self, mock_db):
        game_id = str(uuid4())

        mock_results = [
            MagicMock(
                session_id=uuid4(),
                external_id="ongoing_session",
                game_number=1,
                started_at=datetime.now(timezone.utc),
                session_buy_ins=100000,
                session_cash_outs=80000,
                session_in_game=15000,
                session_net=0,
                player_count=4
            )
        ]

        mock_db.execute.return_value.fetchall.return_value = mock_results

        result = _get_session_analysis(mock_db, game_id)

        assert result[0]['has_significant_in_game'] is True


class TestGetPlayerAnomalies:

    def test_get_player_anomalies_zero_buy_in(self, mock_db):
        game_id = str(uuid4())

        mock_results = [
            MagicMock(
                player_id=uuid4(),
                display_name="Alice",
                external_id="alice@pokernow",
                session_count=3,
                total_buy_ins=10000,
                total_cash_outs=15000,
                total_in_game=0,
                total_net=5000,
                zero_buy_in_count=1,
                zero_cash_out_count=0
            )
        ]

        mock_db.execute.return_value.fetchall.return_value = mock_results

        result = _get_player_anomalies(mock_db, game_id)

        assert len(result) == 1
        assert "1 sessions with zero buy-ins" in result[0]['issues']

    def test_get_player_anomalies_cash_out_without_buy_in(self, mock_db):
        game_id = str(uuid4())

        mock_results = [
            MagicMock(
                player_id=uuid4(),
                display_name="Bob",
                external_id="bob@pokernow",
                session_count=1,
                total_buy_ins=0,
                total_cash_outs=5000,
                total_in_game=0,
                total_net=5000,
                zero_buy_in_count=1,
                zero_cash_out_count=0
            )
        ]

        mock_db.execute.return_value.fetchall.return_value = mock_results

        result = _get_player_anomalies(mock_db, game_id)

        assert len(result) == 1
        assert "Cash-out without buy-in" in result[0]['issues']

    def test_get_player_anomalies_no_issues(self, mock_db):
        game_id = str(uuid4())

        mock_results = [
            MagicMock(
                player_id=uuid4(),
                display_name="Charlie",
                external_id="charlie@pokernow",
                session_count=2,
                total_buy_ins=20000,
                total_cash_outs=25000,
                total_in_game=0,
                total_net=5000,
                zero_buy_in_count=0,
                zero_cash_out_count=0
            )
        ]

        mock_db.execute.return_value.fetchall.return_value = mock_results

        result = _get_player_anomalies(mock_db, game_id)

        assert len(result) == 0


class TestIdentifyProblems:

    def test_identify_problems_unbalanced_sessions(self, mock_db):
        game_id = str(uuid4())

        mock_unbalanced = [
            MagicMock(
                session_id=uuid4(),
                external_id="session1",
                game_number=1,
                balance=-5000
            )
        ]
        mock_db.execute.return_value.fetchall.side_effect = [
            mock_unbalanced,
            [],
            []
        ]

        result = _identify_problems(mock_db, game_id)

        assert len(result['unbalanced_sessions']) == 1
        assert result['unbalanced_sessions'][0]['balance'] == -5000

    def test_identify_problems_missing_data(self, mock_db):
        game_id = str(uuid4())

        mock_missing = [
            MagicMock(
                session_id=uuid4(),
                external_id="orphan_session",
                game_number=5
            )
        ]
        mock_db.execute.return_value.fetchall.side_effect = [
            [],
            mock_missing,
            []
        ]

        result = _identify_problems(mock_db, game_id)

        assert len(result['missing_data_sessions']) == 1
        assert result['missing_data_sessions'][0]['game_number'] == 5

    def test_identify_problems_high_in_game(self, mock_db):
        game_id = str(uuid4())

        mock_high_in_game = [
            MagicMock(
                session_id=uuid4(),
                external_id="session1",
                game_number=1,
                total_in_game=20000,
                total_buy_ins=100000
            )
        ]
        mock_db.execute.return_value.fetchall.side_effect = [
            [],
            [],
            mock_high_in_game
        ]

        result = _identify_problems(mock_db, game_id)

        assert len(result['high_in_game_sessions']) == 1
        assert result['high_in_game_sessions'][0]['percentage'] == 20.0


class TestCheckTemporalConsistency:

    def test_check_temporal_consistency_future_dates(self, mock_db):
        game_id = str(uuid4())
        future_date = datetime.now(timezone.utc)

        mock_future_dates = [
            MagicMock(
                id=uuid4(),
                external_id="future_session",
                game_number=10,
                started_at=future_date
            )
        ]

        mock_db.execute.return_value.fetchall.side_effect = [
            mock_future_dates,
            [],
            []
        ]

        result = _check_temporal_consistency(mock_db, game_id)

        assert len(result['future_dates']) == 1

    def test_check_temporal_consistency_duplicate_game_numbers(self, mock_db):
        game_id = str(uuid4())

        mock_game_numbers = [
            MagicMock(
                game_number=5,
                count=2,
                external_ids=["session1", "session2"],
                session_ids=["id1", "id2"]
            )
        ]

        mock_db.execute.return_value.fetchall.side_effect = [
            [],
            mock_game_numbers,
            []
        ]

        result = _check_temporal_consistency(mock_db, game_id)

        assert len(result['duplicate_game_numbers']) == 1
        assert result['duplicate_game_numbers'][0]['count'] == 2

    def test_check_temporal_consistency_game_number_gaps(self, mock_db):
        game_id = str(uuid4())

        mock_game_numbers = [
            MagicMock(game_number=1, count=1, external_ids=["s1"], session_ids=["id1"]),
            MagicMock(game_number=3, count=1, external_ids=["s3"], session_ids=["id3"]),
            MagicMock(game_number=5, count=1, external_ids=["s5"], session_ids=["id5"])
        ]

        mock_db.execute.return_value.fetchall.side_effect = [
            [],
            mock_game_numbers,
            []
        ]

        result = _check_temporal_consistency(mock_db, game_id)

        assert 2 in result['game_number_gaps']
        assert 4 in result['game_number_gaps']


class TestDetectStatisticalOutliers:

    def test_detect_statistical_outliers_unusual_amounts(self, mock_db):
        game_id = str(uuid4())

        mock_stats = MagicMock(
            avg_buy_in=10000,
            stddev_buy_in=1000,
            avg_cash_out=10000,
            stddev_cash_out=1000,
            avg_abs_net=2000,
            stddev_abs_net=500
        )

        mock_outliers = [
            MagicMock(
                game_number=1,
                external_id="session1",
                display_name="HighRoller",
                buy_in_sum=100000,
                cash_out_sum=50000,
                in_game=0,
                net=-50000,
                buy_in_zscore=90.0,
                cash_out_zscore=40.0
            )
        ]

        mock_db.execute.return_value.fetchone.return_value = mock_stats
        mock_db.execute.return_value.fetchall.return_value = mock_outliers

        result = _detect_statistical_outliers(mock_db, game_id)

        assert len(result['unusual_amounts']) == 1
        assert result['unusual_amounts'][0]['buy_in'] == 100000

    def test_detect_statistical_outliers_suspicious_round_numbers(self, mock_db):
        game_id = str(uuid4())

        mock_stats = MagicMock(avg_buy_in=None)
        mock_db.execute.return_value.fetchone.return_value = mock_stats

        mock_round_numbers = [
            MagicMock(
                display_name="RoundPlayer",
                total_entries=5,
                round_buy_ins=4,
                round_cash_outs=4
            )
        ]

        mock_db.execute.return_value.fetchall.return_value = mock_round_numbers

        result = _detect_statistical_outliers(mock_db, game_id)

        assert len(result['suspicious_round_numbers']) == 1
        assert result['suspicious_round_numbers'][0]['round_percentage'] == 80.0


class TestValidateCrossSessionData:

    def test_validate_cross_session_data_external_id_conflicts(self, mock_db):
        game_id = str(uuid4())

        mock_conflicts = [
            MagicMock(
                player1_id=uuid4(),
                name1="Alice Smith",
                external_id="alice@pokernow",
                player2_id=uuid4(),
                name2="Alice Jones",
                sessions1=3,
                sessions2=2
            )
        ]

        mock_db.execute.return_value.fetchall.side_effect = [
            mock_conflicts,
            []
        ]

        result = _validate_cross_session_data(mock_db, game_id)

        assert len(result['external_id_conflicts']) == 1
        assert result['external_id_conflicts'][0]['external_id'] == "alice@pokernow"

    def test_validate_cross_session_data_name_variations(self, mock_db):
        game_id = str(uuid4())

        mock_variations = [
            MagicMock(
                player1_id=uuid4(),
                name1="Bob",
                player2_id=uuid4(),
                name2="bob",
                sessions1=2,
                sessions2=3
            )
        ]

        mock_db.execute.return_value.fetchall.side_effect = [
            [],
            mock_variations
        ]

        result = _validate_cross_session_data(mock_db, game_id)

        assert len(result['name_variations']) == 1


class TestCheckBusinessLogicViolations:

    def test_check_business_logic_violations_negative_amounts(self, mock_db):
        game_id = str(uuid4())

        mock_negative = [
            MagicMock(
                game_number=1,
                external_id="session1",
                display_name="Alice",
                buy_in_sum=-5000,
                cash_out_sum=10000,
                in_game=0,
                net=15000
            )
        ]

        mock_db.execute.return_value.fetchall.side_effect = [
            mock_negative,
            []
        ]

        result = _check_business_logic_violations(mock_db, game_id)

        assert len(result['negative_amounts']) == 1
        assert result['negative_amounts'][0]['buy_in'] == -5000

    def test_check_business_logic_violations_mathematical_inconsistencies(self, mock_db):
        game_id = str(uuid4())

        mock_math_errors = [
            MagicMock(
                session_id=uuid4(),
                player_id=uuid4(),
                game_number=1,
                external_id="session1",
                display_name="Bob",
                buy_in_sum=10000,
                cash_out_sum=15000,
                in_game=0,
                net=6000,
                names=["Bob"],
                calculated_net=5000,
                difference=1000
            )
        ]

        mock_db.execute.return_value.fetchall.side_effect = [
            [],
            mock_math_errors
        ]

        result = _check_business_logic_violations(mock_db, game_id)

        assert len(result['mathematical_inconsistencies']) == 1
        assert result['mathematical_inconsistencies'][0]['recorded_net'] == 6000
        assert result['mathematical_inconsistencies'][0]['calculated_net'] == 5000
        assert result['mathematical_inconsistencies'][0]['difference'] == 1000


class TestCheckPaymentLedgerBalance:

    def test_check_payment_ledger_balance_balanced(self, mock_db):
        game_id = str(uuid4())

        mock_balances = [
            MagicMock(
                player_id=uuid4(),
                display_name="Alice",
                poker_net_winnings=50000,
                total_paid=20000,
                total_received=30000,
                payment_balance=0
            ),
            MagicMock(
                player_id=uuid4(),
                display_name="Bob",
                poker_net_winnings=-50000,
                total_paid=30000,
                total_received=20000,
                payment_balance=0
            )
        ]

        mock_db.execute.return_value.fetchall.return_value = mock_balances

        result = _check_payment_ledger_balance(mock_db, game_id)

        assert result['is_balanced'] is True
        assert result['total_balance'] == 0
        assert len(result['issues']) == 0

    def test_check_payment_ledger_balance_imbalanced(self, mock_db):
        game_id = str(uuid4())

        mock_balances = [
            MagicMock(
                player_id=uuid4(),
                display_name="Alice",
                poker_net_winnings=50000,
                total_paid=10000,
                total_received=30000,
                payment_balance=10000
            )
        ]

        mock_db.execute.return_value.fetchall.return_value = mock_balances

        result = _check_payment_ledger_balance(mock_db, game_id)

        assert result['is_balanced'] is False
        assert result['total_balance'] == 10000
        assert len(result['issues']) > 0

    def test_check_payment_ledger_balance_no_balances(self, mock_db):
        game_id = str(uuid4())
        mock_db.execute.return_value.fetchall.return_value = []

        result = _check_payment_ledger_balance(mock_db, game_id)

        assert result['is_balanced'] is True
        assert result['total_balance'] == 0


class TestGetLedgerAnalysis:

    def test_get_ledger_analysis_comprehensive(self, mock_db, sample_game):
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_game

        with patch('services.ledger_analysis_service.SessionLocal', return_value=mock_db):
            with patch('services.ledger_analysis_service._get_overall_balance', return_value={'balance': 0}):
                with patch('services.ledger_analysis_service._get_session_analysis', return_value=[]):
                    with patch('services.ledger_analysis_service._get_player_anomalies', return_value=[]):
                        with patch('services.ledger_analysis_service._identify_problems', return_value={}):
                            with patch('services.ledger_analysis_service._check_temporal_consistency', return_value={}):
                                with patch('services.ledger_analysis_service._detect_statistical_outliers', return_value={}):
                                    with patch('services.ledger_analysis_service._validate_cross_session_data', return_value={}):
                                        with patch('services.ledger_analysis_service._check_business_logic_violations', return_value={}):
                                            with patch('services.ledger_analysis_service._check_payment_ledger_balance', return_value={}):
                                                result = get_ledger_analysis("TEST123")

        assert result['game_code'] == "TEST123"
        assert 'overall_balance' in result
        assert 'session_analysis' in result
        assert 'player_anomalies' in result
        assert 'problems' in result
        assert 'temporal_issues' in result
        assert 'statistical_outliers' in result
        assert 'cross_session_issues' in result
        assert 'business_logic_violations' in result
        assert 'payment_balance_check' in result


class TestGetSessionDetail:

    def test_get_session_detail_success(self, mock_db):
        session_id = str(uuid4())
        session = SessionModel(
            id=session_id,
            external_id="session1",
            game_number=5,
            started_at=datetime.now(timezone.utc),
            end_session_json={}
        )

        player_data = [
            MagicMock(
                player_id=uuid4(),
                display_name="Alice",
                buy_in_sum=10000,
                cash_out_sum=15000,
                in_game=0,
                net=5000
            )
        ]

        mock_db.execute.return_value.scalar_one_or_none.return_value = session
        mock_db.execute.return_value.fetchall.side_effect = [player_data, []]
        mock_db.__enter__ = Mock(return_value=mock_db)
        mock_db.__exit__ = Mock(return_value=None)

        with patch('services.ledger_analysis_service.SessionLocal', return_value=mock_db):
            result = get_session_detail(session_id)

        assert result['session_id'] == str(session_id)
        assert result['game_number'] == 5
        assert len(result['players']) == 1
        assert result['totals']['buy_ins'] == 10000
        assert result['totals']['cash_outs'] == 15000
        assert result['totals']['balance'] == -5000


class TestRecalculateSessionBalance:

    def test_recalculate_session_balance_no_fixes_needed(self, mock_db):
        session_id = str(uuid4())
        session = SessionModel(id=session_id, external_id="session1", game_number=1)

        player_summaries = [
            MagicMock(
                player_id=uuid4(),
                buy_in_sum=10000,
                cash_out_sum=15000,
                in_game=0,
                net=5000
            )
        ]

        mock_db.execute.return_value.scalar_one_or_none.return_value = session
        mock_db.execute.return_value.fetchall.return_value = player_summaries

        with patch('services.ledger_analysis_service.SessionLocal', return_value=mock_db):
            result = recalculate_session_balance(session_id)

        assert result['fixes_applied'] == 0
        assert result['is_balanced'] is True