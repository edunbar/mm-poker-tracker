"""
Game Management API Integration Tests

Tests core game management endpoints including game creation, session ingestion,
and game data retrieval with full end-to-end validation.
"""

import pytest
import uuid
from flask import Flask
from src.app import create_app
from src.db.database import SessionLocal
from src.db.models import Game, Player, Session as SessionModel, SessionPlayerSummary
from datetime import datetime


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    with app.test_client() as client:
        yield client


@pytest.fixture
def test_game():
    """Create a test game with admin code."""
    db = SessionLocal()
    try:
        unique_id = str(uuid.uuid4())[:8].upper()
        game = Game(
            public_code=f"TST{unique_id}",  # Use full unique_id to avoid collisions
            admin_code=f"test_admin_code_{unique_id}",
            title=f"Test Game API {unique_id}"
        )
        db.add(game)
        db.commit()
        yield game
    finally:
        db.close()


class TestGameCreation:
    """Test game creation API endpoint."""

    def test_create_game_no_title(self, client):
        """Create game without title should succeed with default title."""
        response = client.post('/api/games/create',
            json={}
        )

        assert response.status_code == 201
        data = response.get_json()

        # Verify response structure
        required_fields = ['game_id', 'public_code', 'admin_code', 'title', 'created_at']
        for field in required_fields:
            assert field in data

        # Verify public code format (5 characters)
        assert len(data['public_code']) == 5
        assert data['public_code'].isalnum()

        # Verify admin code is long and secure
        assert len(data['admin_code']) >= 30

        # Verify game_id is UUID format
        assert len(data['game_id']) == 36  # UUID with hyphens

    def test_create_game_with_title(self, client):
        """Create game with custom title."""
        custom_title = f"Custom Test Game {uuid.uuid4()}"

        response = client.post('/api/games/create',
            json={'title': custom_title}
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['title'] == custom_title

    def test_create_game_invalid_title_empty(self, client):
        """Empty title should be rejected."""
        response = client.post('/api/games/create',
            json={'title': ''}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Invalid title' in data['error']

    def test_create_game_invalid_title_too_long(self, client):
        """Title that's too long should be rejected."""
        long_title = "x" * 201  # Assuming 200 char limit

        response = client.post('/api/games/create',
            json={'title': long_title}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Invalid title' in data['error']

    def test_create_game_invalid_json(self, client):
        """Invalid JSON should be handled gracefully."""
        response = client.post('/api/games/create',
            data='invalid json',
            content_type='application/json'
        )

        # Should either succeed with empty body or return 400
        assert response.status_code in [201, 400]

    def test_create_multiple_games_unique_codes(self, client):
        """Multiple games should have unique codes."""
        # Create first game
        response1 = client.post('/api/games/create', json={})
        assert response1.status_code == 201
        game1 = response1.get_json()

        # Create second game
        response2 = client.post('/api/games/create', json={})
        assert response2.status_code == 201
        game2 = response2.get_json()

        # Verify codes are unique
        assert game1['public_code'] != game2['public_code']
        assert game1['admin_code'] != game2['admin_code']
        assert game1['game_id'] != game2['game_id']


class TestSessionIngestion:
    """Test session upload/ingestion endpoints."""

    def test_upload_session_valid_data(self, client, test_game):
        """Upload valid session data."""
        session_id = f"test_session_{uuid.uuid4()}"

        response = client.post('/api/games/upload',
            json={
                "public_code": test_game.public_code,
                "sessionId": session_id,
                "game_data": {
                    "playersInfos": {
                        "player1": {
                            "id": "player1",
                            "name": "Alice Test",
                            "buyInSum": 10000,
                            "buyOutSum": 15000,
                            "net": 5000
                        },
                        "player2": {
                            "id": "player2",
                            "name": "Bob Test",
                            "buyInSum": 20000,
                            "buyOutSum": 15000,
                            "net": -5000
                        }
                    }
                }
            },
            headers={'X-Admin-Code': test_game.admin_code}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['session_id'] == session_id
        assert 'players_processed' in data

    def test_upload_session_missing_public_code(self, client, test_game):
        """Missing public code should be rejected."""
        response = client.post('/api/games/upload',
            json={
                "sessionId": "test_session_123",
                "game_data": {"playersInfos": {}}
            },
            headers={'X-Admin-Code': test_game.admin_code}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'public_code is required' in data['error']

    def test_upload_session_missing_session_id(self, client, test_game):
        """Missing session ID should be rejected."""
        response = client.post('/api/games/upload',
            json={
                "public_code": test_game.public_code,
                "game_data": {"playersInfos": {}}
            },
            headers={'X-Admin-Code': test_game.admin_code}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'sessionId is required' in data['error']

    def test_upload_session_invalid_public_code(self, client, test_game):
        """Invalid public code should be rejected."""
        response = client.post('/api/games/upload',
            json={
                "public_code": "INVALID",
                "sessionId": "test_session_456",
                "game_data": {"playersInfos": {}}
            },
            headers={'X-Admin-Code': test_game.admin_code}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

    def test_upload_session_with_date_override(self, client, test_game):
        """Upload session with custom date."""
        response = client.post('/api/games/upload',
            json={
                "public_code": test_game.public_code,
                "sessionId": f"date_test_{uuid.uuid4()}",
                "date": "2024-01-15T18:00:00",
                "game_data": {
                    "playersInfos": {
                        "player1": {
                            "id": "player1",
                            "name": "Alice",
                            "buyInSum": 10000,
                            "buyOutSum": 12000,
                            "net": 2000
                        }
                    }
                }
            },
            headers={'X-Admin-Code': test_game.admin_code}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_upload_session_with_game_number_override(self, client, test_game):
        """Upload session with manual game number."""
        response = client.post('/api/games/upload',
            json={
                "public_code": test_game.public_code,
                "sessionId": f"game_num_test_{uuid.uuid4()}",
                "gameNumber": 42,
                "game_data": {
                    "playersInfos": {
                        "player1": {
                            "id": "player1",
                            "name": "Alice",
                            "buyInSum": 10000,
                            "buyOutSum": 12000,
                            "net": 2000
                        }
                    }
                }
            },
            headers={'X-Admin-Code': test_game.admin_code}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True


class TestLiveGameUpload:
    """Test live game data upload endpoint."""

    def test_upload_live_game_valid_data(self, client, test_game):
        """Upload valid live game data."""
        response = client.post('/api/games/upload_live',
            json={
                "public_code": test_game.public_code,
                "session_name": f"Live Game {uuid.uuid4()}",
                "players": [
                    {
                        "name": "Alice Live",
                        "buy_in": 100.0,
                        "cash_out": 150.0,
                        "in_game": 0.0
                    },
                    {
                        "name": "Bob Live",
                        "buy_in": 200.0,
                        "cash_out": 175.0,
                        "in_game": 25.0
                    }
                ]
            },
            headers={'X-Admin-Code': test_game.admin_code}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'balance_validation' in data
        assert 'session_id' in data

    def test_upload_live_game_missing_session_name(self, client, test_game):
        """Missing session name should be rejected."""
        response = client.post('/api/games/upload_live',
            json={
                "public_code": test_game.public_code,
                "players": [
                    {"name": "Alice", "buy_in": 100.0, "cash_out": 150.0, "in_game": 0.0}
                ]
            },
            headers={'X-Admin-Code': test_game.admin_code}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'session_name is required' in data['error']

    def test_upload_live_game_empty_players(self, client, test_game):
        """Empty players array should be rejected."""
        response = client.post('/api/games/upload_live',
            json={
                "public_code": test_game.public_code,
                "session_name": "Empty Players Test",
                "players": []
            },
            headers={'X-Admin-Code': test_game.admin_code}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'players array is required' in data['error']

    def test_upload_live_game_invalid_player_data(self, client, test_game):
        """Invalid player data should be rejected."""
        response = client.post('/api/games/upload_live',
            json={
                "public_code": test_game.public_code,
                "session_name": "Invalid Player Test",
                "players": [
                    {
                        "name": "",  # Empty name should be invalid
                        "buy_in": 100.0,
                        "cash_out": 150.0,
                        "in_game": 0.0
                    }
                ]
            },
            headers={'X-Admin-Code': test_game.admin_code}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Invalid player data' in data['error']

    def test_upload_live_game_balance_validation(self, client, test_game):
        """Live game upload should include balance validation."""
        response = client.post('/api/games/upload_live',
            json={
                "public_code": test_game.public_code,
                "session_name": "Balance Test",
                "players": [
                    {"name": "Alice", "buy_in": 100.0, "cash_out": 80.0, "in_game": 20.0},
                    {"name": "Bob", "buy_in": 200.0, "cash_out": 200.0, "in_game": 0.0}
                ]
            },
            headers={'X-Admin-Code': test_game.admin_code}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'balance_validation' in data

        validation = data['balance_validation']
        assert 'balanced' in validation
        assert 'total_buy_ins' in validation
        assert 'total_cash_outs' in validation
        assert 'total_in_game' in validation


class TestGameDataRetrieval:
    """Test game data retrieval endpoints that use public codes."""

    def setup_game_with_data(self):
        """Helper to create game with test data."""
        db = SessionLocal()
        try:
            unique_id = str(uuid.uuid4())[:8].upper()
            game = Game(
                public_code=f"RET{unique_id}",
                admin_code=f"admin_{unique_id}",
                title=f"Retrieval Test Game {unique_id}"
            )
            db.add(game)
            db.flush()

            # Create players
            player1 = Player(display_name="Alice Retrieve", external_id=f"alice_{unique_id}")
            player2 = Player(display_name="Bob Retrieve", external_id=f"bob_{unique_id}")
            db.add_all([player1, player2])
            db.flush()

            # Create session
            session = SessionModel(
                game_id=game.id,
                external_id=f"retrieval_session_{unique_id}",
                session_type="test"
            )
            db.add(session)
            db.flush()

            # Create session summaries
            summary1 = SessionPlayerSummary(
                session_id=session.id,
                player_id=player1.id,
                buy_in_sum=10000,
                cash_out_sum=15000,
                in_game=0,
                net=5000,
                names=[player1.display_name]
            )
            summary2 = SessionPlayerSummary(
                session_id=session.id,
                player_id=player2.id,
                buy_in_sum=20000,
                cash_out_sum=15000,
                in_game=0,
                net=-5000,
                names=[player2.display_name]
            )
            db.add_all([summary1, summary2])
            db.commit()

            return game

        finally:
            db.close()

    def test_get_game_summary(self, client):
        """Test getting game summary with public code."""
        game = self.setup_game_with_data()

        response = client.get(f'/api/games/{game.public_code}/summary')

        assert response.status_code == 200
        data = response.get_json()

        # Verify response structure
        assert 'title' in data
        assert 'rows' in data
        assert len(data['rows']) == 2  # Two players

        # Verify player data structure
        for row in data['rows']:
            required_fields = ['player', 'rank', 'buyIn', 'cashOut', 'net', 'gamesPlayed']
            for field in required_fields:
                assert field in row

    def test_get_game_analytics(self, client):
        """Test getting game analytics with public code."""
        game = self.setup_game_with_data()

        response = client.get(f'/api/games/{game.public_code}/analytics')

        assert response.status_code == 200
        data = response.get_json()

        assert 'analytics' in data
        assert isinstance(data['analytics'], dict)

        # Should have analytics for both players
        assert len(data['analytics']) >= 2

    def test_get_session_extremes(self, client):
        """Test getting session extremes with public code."""
        game = self.setup_game_with_data()

        response = client.get(f'/api/games/{game.public_code}/extremes')

        assert response.status_code == 200
        data = response.get_json()

        assert 'best_sessions' in data
        assert 'worst_sessions' in data
        assert isinstance(data['best_sessions'], list)
        assert isinstance(data['worst_sessions'], list)

    def test_get_game_summary_invalid_public_code(self, client):
        """Invalid public code should return 404."""
        response = client.get('/api/games/INVALID/summary')

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

    def test_get_game_analytics_nonexistent_game(self, client):
        """Non-existent game should return 404."""
        response = client.get('/api/games/XXXXX/analytics')

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data


class TestTransactionService:
    """Test PokerNow transaction retrieval."""

    def test_get_transactions_valid_url(self, client):
        """Test transaction retrieval with valid URL."""
        # Note: This test may need to be mocked if it makes external calls
        test_url = "https://www.pokernow.club/games/test-game-123"

        response = client.get('/api/games/get_transactions',
            query_string={'url': test_url}
        )

        # May return 200 with data or 500 if external service unavailable
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.get_json()
            # Should return transaction data structure
            assert isinstance(data, (dict, list))

    def test_get_transactions_missing_url(self, client):
        """Missing URL parameter should be rejected."""
        response = client.get('/api/games/get_transactions')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'URL parameter is missing' in data['error']

    def test_get_transactions_empty_url(self, client):
        """Empty URL parameter should be rejected."""
        response = client.get('/api/games/get_transactions',
            query_string={'url': ''}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'URL parameter is missing' in data['error']

    def test_get_transactions_whitespace_url(self, client):
        """Whitespace-only URL should be rejected."""
        response = client.get('/api/games/get_transactions',
            query_string={'url': '   '}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'URL parameter is missing' in data['error']


class TestServiceInfo:
    """Test service information endpoint."""

    def test_get_service_info(self, client):
        """Test service info endpoint."""
        response = client.get('/api/games/service-info')

        assert response.status_code == 200
        data = response.get_json()

        # Should contain service version information
        assert isinstance(data, dict)
        # Common service info fields
        expected_fields = ['ledger_service', 'game_summary_service', 'use_domain_services']

        # At least some service info should be present
        assert len(data) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])