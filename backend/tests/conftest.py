import sys
import os
from pathlib import Path

# Add src directory to Python path for imports
backend_dir = Path(__file__).parent.parent
src_dir = backend_dir / "src"
sys.path.insert(0, str(src_dir))

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import MagicMock

from db.models import Game, Player, Session, SessionPlayerSummary, PaymentTransaction, PaymentBalance


@pytest.fixture
def mock_uuid():
    return uuid4()


@pytest.fixture
def mock_datetime():
    return datetime.now(timezone.utc)


@pytest.fixture
def sample_game_data():
    return {
        'id': uuid4(),
        'public_code': 'TEST123',
        'admin_code': 'test-admin-secret-token-12345',
        'title': 'Test Poker Game',
        'created_at': datetime.now(timezone.utc)
    }


@pytest.fixture
def sample_game(sample_game_data):
    return Game(**sample_game_data)


@pytest.fixture
def sample_players_data():
    return [
        {
            'id': uuid4(),
            'display_name': 'Alice',
            'external_id': 'alice@pokernow',
            'created_at': datetime.now(timezone.utc)
        },
        {
            'id': uuid4(),
            'display_name': 'Bob',
            'external_id': 'bob@pokernow',
            'created_at': datetime.now(timezone.utc)
        },
        {
            'id': uuid4(),
            'display_name': 'Charlie',
            'external_id': 'charlie@pokernow',
            'created_at': datetime.now(timezone.utc)
        }
    ]


@pytest.fixture
def sample_players(sample_players_data):
    return [Player(**data) for data in sample_players_data]


@pytest.fixture
def sample_session_data(sample_game):
    return {
        'id': uuid4(),
        'game_id': sample_game.id,
        'external_id': 'pokernow_session_abc123',
        'game_number': 5,
        'started_at': datetime.now(timezone.utc),
        'ended_at': datetime.now(timezone.utc),
        'end_session_json': {}
    }


@pytest.fixture
def sample_session(sample_session_data):
    return Session(**sample_session_data)


@pytest.fixture
def sample_session_player_summary_data(sample_session, sample_players):
    player = sample_players[0]
    return {
        'session_id': sample_session.id,
        'player_id': player.id,
        'buy_in_sum': 10000,
        'cash_out_sum': 15000,
        'in_game': 0,
        'net': 5000,
        'names': [player.display_name]
    }


@pytest.fixture
def sample_session_player_summary(sample_session_player_summary_data):
    return SessionPlayerSummary(**sample_session_player_summary_data)


@pytest.fixture
def sample_payment_transaction_data(sample_game, sample_players):
    alice, bob, _ = sample_players
    return {
        'id': uuid4(),
        'game_id': sample_game.id,
        'payer_id': alice.id,
        'recipient_id': bob.id,
        'amount_cents': 10000,
        'payment_method': 'Venmo',
        'payment_date': datetime.now(timezone.utc),
        'status': 'completed',
        'notes': 'Test payment',
        'reference_id': 'venmo_123',
        'created_by': 'admin',
        'created_at': datetime.now(timezone.utc)
    }


@pytest.fixture
def sample_payment_transaction(sample_payment_transaction_data):
    return PaymentTransaction(**sample_payment_transaction_data)


@pytest.fixture
def sample_payment_balance_data(sample_game, sample_players):
    alice = sample_players[0]
    return {
        'id': uuid4(),
        'game_id': sample_game.id,
        'player_id': alice.id,
        'poker_net_winnings': 50000,
        'total_paid': 20000,
        'total_received': 10000,
        'payment_balance': 40000,
        'last_updated': datetime.now(timezone.utc)
    }


@pytest.fixture
def sample_payment_balance(sample_payment_balance_data):
    return PaymentBalance(**sample_payment_balance_data)


@pytest.fixture
def balanced_game_session_data(sample_game, sample_players):
    alice, bob, charlie = sample_players
    session_id = uuid4()

    return {
        'session': {
            'id': session_id,
            'game_id': sample_game.id,
            'external_id': 'balanced_session',
            'game_number': 1,
            'started_at': datetime.now(timezone.utc),
            'ended_at': datetime.now(timezone.utc)
        },
        'summaries': [
            {
                'session_id': session_id,
                'player_id': alice.id,
                'buy_in_sum': 10000,
                'cash_out_sum': 15000,
                'in_game': 0,
                'net': 5000,
                'names': ['Alice']
            },
            {
                'session_id': session_id,
                'player_id': bob.id,
                'buy_in_sum': 10000,
                'cash_out_sum': 8000,
                'in_game': 0,
                'net': -2000,
                'names': ['Bob']
            },
            {
                'session_id': session_id,
                'player_id': charlie.id,
                'buy_in_sum': 10000,
                'cash_out_sum': 7000,
                'in_game': 0,
                'net': -3000,
                'names': ['Charlie']
            }
        ]
    }


@pytest.fixture
def imbalanced_game_session_data(sample_game, sample_players):
    alice, bob = sample_players[:2]
    session_id = uuid4()

    return {
        'session': {
            'id': session_id,
            'game_id': sample_game.id,
            'external_id': 'imbalanced_session',
            'game_number': 2,
            'started_at': datetime.now(timezone.utc),
            'ended_at': datetime.now(timezone.utc)
        },
        'summaries': [
            {
                'session_id': session_id,
                'player_id': alice.id,
                'buy_in_sum': 10000,
                'cash_out_sum': 15000,
                'in_game': 0,
                'net': 5000,
                'names': ['Alice']
            },
            {
                'session_id': session_id,
                'player_id': bob.id,
                'buy_in_sum': 10000,
                'cash_out_sum': 3000,
                'in_game': 0,
                'net': -7000,
                'names': ['Bob']
            }
        ]
    }


@pytest.fixture
def mock_db_session():
    db = MagicMock()
    db.query = MagicMock()
    db.add = MagicMock()
    db.commit = MagicMock()
    db.rollback = MagicMock()
    db.flush = MagicMock()
    db.delete = MagicMock()
    db.execute = MagicMock()

    db.__enter__ = MagicMock(return_value=db)
    db.__exit__ = MagicMock(return_value=None)

    return db


@pytest.fixture
def payment_summary_factory():
    def _create_payment_summary(
        player_id=None,
        player_name="Test Player",
        poker_net_winnings=Decimal("0"),
        total_paid=Decimal("0"),
        total_received=Decimal("0"),
        days_since_last_payment=None
    ):
        from services.payment_service import PlayerPaymentSummary

        if player_id is None:
            player_id = str(uuid4())

        balance = total_received - poker_net_winnings
        realized_earnings = total_received - total_paid

        return PlayerPaymentSummary(
            player_id=player_id,
            player_name=player_name,
            poker_net_winnings=poker_net_winnings,
            total_paid=total_paid,
            total_received=total_received,
            balance=balance,
            realized_earnings=realized_earnings,
            days_since_last_payment=days_since_last_payment
        )

    return _create_payment_summary


@pytest.fixture
def settlement_suggestion_factory():
    def _create_settlement_suggestion(
        payer_id=None,
        payer_name="Payer",
        recipient_id=None,
        recipient_name="Recipient",
        amount=Decimal("0")
    ):
        from services.payment_service import SettlementSuggestion

        if payer_id is None:
            payer_id = str(uuid4())
        if recipient_id is None:
            recipient_id = str(uuid4())

        return SettlementSuggestion(
            payer_id=payer_id,
            payer_name=payer_name,
            recipient_id=recipient_id,
            recipient_name=recipient_name,
            amount=amount
        )

    return _create_settlement_suggestion


# ============================================================================
# Authentication Testing Fixtures
# ============================================================================

@pytest.fixture(scope='session', autouse=True)
def setup_test_environment():
    """Set up test environment variables"""
    os.environ['JWT_SECRET'] = 'test_secret_key_for_testing'
    os.environ['FLASK_ENV'] = 'testing'
    yield


@pytest.fixture
def test_client():
    """Provide Flask test client for HTTP testing"""
    from app import create_app
    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()


@pytest.fixture
def db_session():
    """Provide a database session for tests"""
    from db.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@pytest.fixture
def register_user(test_client):
    """
    Helper fixture to register a user and return (user_data, token).

    Usage:
        user, token = register_user('test@example.com', 'password123', 'Test User')
    """
    def _register(email, password, display_name='Test User'):
        response = test_client.post('/api/auth/register', json={
            'email': email,
            'password': password,
            'display_name': display_name
        })
        data = response.get_json()
        if response.status_code != 201:
            raise AssertionError(f"Registration failed: {data}")
        return data['user'], data['access_token']
    return _register


@pytest.fixture
def create_game(db_session):
    """
    Helper fixture to create a game.

    Usage:
        game = create_game(public_code='TEST123', owner_id=user_id)
    """
    def _create(public_code=None, admin_code=None, owner_id=None, title='Test Game'):
        if not public_code:
            public_code = f"TEST{uuid4().hex[:6].upper()}"
        if not admin_code:
            admin_code = f"admin-{uuid4()}"

        game = Game(
            public_code=public_code,
            admin_code=admin_code,
            title=title,
            owner_user_id=owner_id
        )
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)
        return game
    return _create


@pytest.fixture
def auth_headers():
    """
    Helper fixture to create auth headers from token.

    Usage:
        headers = auth_headers(token)
    """
    def _headers(token):
        return {'Authorization': f'Bearer {token}'}
    return _headers


@pytest.fixture
def admin_code_headers():
    """
    Helper fixture to create admin code headers.

    Usage:
        headers = admin_code_headers(admin_code)
    """
    def _headers(admin_code):
        return {'X-Admin-Code': admin_code}
    return _headers