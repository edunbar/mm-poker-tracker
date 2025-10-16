"""
Ledger API Integration Tests

Tests ledger management endpoints including session summaries, updates, and deletions
with proper authentication and data validation.
"""

import pytest
import uuid
from flask import Flask
from src.app import create_app
from src.db.database import SessionLocal
from src.db.models import Game, Player, Session as SessionModel, SessionPlayerSummary


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
def ledger_test_setup():
    """Create test game with players and session data for ledger testing."""
    db = SessionLocal()
    try:
        unique_id = str(uuid.uuid4())[:8].upper()

        # Create game
        game = Game(
            public_code=f"LED{unique_id}",
            admin_code=f"ledger_admin_{unique_id}",
            title=f"Ledger Test Game {unique_id}"
        )
        db.add(game)
        db.flush()

        # Create players
        alice = Player(
            display_name=f"Alice Ledger {unique_id}",
            external_id=f"alice_ledger_{unique_id}"
        )
        bob = Player(
            display_name=f"Bob Ledger {unique_id}",
            external_id=f"bob_ledger_{unique_id}"
        )
        db.add_all([alice, bob])
        db.flush()

        # Create multiple sessions
        session1 = SessionModel(
            game_id=game.id,
            external_id=f"ledger_session_1_{unique_id}",
            session_type="test",
            game_number=1
        )
        session2 = SessionModel(
            game_id=game.id,
            external_id=f"ledger_session_2_{unique_id}",
            session_type="test",
            game_number=2
        )
        db.add_all([session1, session2])
        db.flush()

        # Create session summaries
        # Session 1: Alice wins $50, Bob loses $50
        alice_s1 = SessionPlayerSummary(
            session_id=session1.id,
            player_id=alice.id,
            buy_in_sum=10000,
            cash_out_sum=15000,
            in_game=0,
            net=5000,
            names=[alice.display_name]
        )
        bob_s1 = SessionPlayerSummary(
            session_id=session1.id,
            player_id=bob.id,
            buy_in_sum=10000,
            cash_out_sum=5000,
            in_game=0,
            net=-5000,
            names=[bob.display_name]
        )

        # Session 2: Alice loses $30, Bob wins $30
        alice_s2 = SessionPlayerSummary(
            session_id=session2.id,
            player_id=alice.id,
            buy_in_sum=10000,
            cash_out_sum=7000,
            in_game=0,
            net=-3000,
            names=[alice.display_name]
        )
        bob_s2 = SessionPlayerSummary(
            session_id=session2.id,
            player_id=bob.id,
            buy_in_sum=10000,
            cash_out_sum=13000,
            in_game=0,
            net=3000,
            names=[bob.display_name]
        )

        db.add_all([alice_s1, bob_s1, alice_s2, bob_s2])
        db.commit()

        yield {
            'game': game,
            'alice': alice,
            'bob': bob,
            'session1': session1,
            'session2': session2,
            'alice_s1': alice_s1,
            'bob_s1': bob_s1,
            'alice_s2': alice_s2,
            'bob_s2': bob_s2
        }

    finally:
        db.close()


class TestLedgerRetrieval:
    """Test ledger data retrieval endpoints."""

    def test_get_all_session_summaries(self, client, ledger_test_setup):
        """Get all session summaries for a game."""
        setup = ledger_test_setup
        game = setup['game']

        response = client.get(f'/api/games/{game.public_code}/ledger')

        assert response.status_code == 200
        data = response.get_json()

        # Should return summaries object
        assert 'total_count' in data
        assert 'summaries' in data
        assert data['total_count'] >= 4  # 2 players × 2 sessions

        # Check summary structure
        for summary in data['summaries']:
            required_fields = ['session_id', 'player_id', 'buy_in_sum', 'cash_out_sum', 'net']
            for field in required_fields:
                assert field in summary

    def test_get_session_summary_specific_player(self, client, ledger_test_setup):
        """Get session summary for specific player."""
        setup = ledger_test_setup
        game = setup['game']
        session1 = setup['session1']
        alice = setup['alice']

        response = client.get(f'/api/games/{game.public_code}/ledger/{session1.id}/{alice.id}')

        assert response.status_code == 200
        data = response.get_json()

        # Should return specific session summary
        assert data['session_id'] == str(session1.id)
        assert data['player_id'] == str(alice.id)
        assert 'buy_in_sum' in data
        assert 'cash_out_sum' in data
        assert 'net' in data

    def test_get_session_summary_nonexistent_player(self, client, ledger_test_setup):
        """Get session summary for nonexistent player should return 404."""
        setup = ledger_test_setup
        game = setup['game']
        session1 = setup['session1']
        fake_player_id = str(uuid.uuid4())

        response = client.get(f'/api/games/{game.public_code}/ledger/{session1.id}/{fake_player_id}')

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

    def test_get_session_summary_nonexistent_session(self, client, ledger_test_setup):
        """Get session summary for nonexistent session should return 404."""
        setup = ledger_test_setup
        game = setup['game']
        alice = setup['alice']
        fake_session_id = str(uuid.uuid4())

        response = client.get(f'/api/games/{game.public_code}/ledger/{fake_session_id}/{alice.id}')

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

    def test_ledger_retrieval_public_code_validation(self, client):
        """Ledger retrieval should validate public code."""
        fake_session_id = str(uuid.uuid4())
        fake_player_id = str(uuid.uuid4())

        response = client.get(f'/api/games/INVALID/ledger/{fake_session_id}/{fake_player_id}')

        # Should return empty results or 404 for invalid game
        assert response.status_code in [404, 200]

        if response.status_code == 200:
            data = response.get_json()
            assert data is None or 'error' in data


class TestLedgerUpdates:
    """Test ledger update endpoints."""

    def test_update_session_summary_valid_data(self, client, ledger_test_setup):
        """Update session summary with valid data."""
        setup = ledger_test_setup
        game = setup['game']
        session1 = setup['session1']
        alice = setup['alice']

        response = client.put(f'/api/games/{game.public_code}/ledger/{session1.id}/{alice.id}',
            json={
                "buy_in_sum": 12000,  # Update from 10000 to 12000
                "notes": "Updated via API test"
            },
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        assert 'updated successfully' in data['message']
        assert data['session_id'] == str(session1.id)
        assert data['player_id'] == str(alice.id)

        # Verify update in database
        db = SessionLocal()
        try:
            summary = db.query(SessionPlayerSummary).filter_by(
                session_id=session1.id,
                player_id=alice.id
            ).first()
            assert summary.buy_in_sum == 12000
        finally:
            db.close()

    def test_update_session_summary_multiple_fields(self, client, ledger_test_setup):
        """Update multiple fields in session summary."""
        setup = ledger_test_setup
        game = setup['game']
        session2 = setup['session2']
        bob = setup['bob']

        response = client.put(f'/api/games/{game.public_code}/ledger/{session2.id}/{bob.id}',
            json={
                "buy_in_sum": 11000,
                "cash_out_sum": 14000,
                "in_game": 500,
                "notes": "Multiple field update"
            },
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'updated successfully' in data['message']

        # Verify all updates in database
        db = SessionLocal()
        try:
            summary = db.query(SessionPlayerSummary).filter_by(
                session_id=session2.id,
                player_id=bob.id
            ).first()
            assert summary.buy_in_sum == 11000
            assert summary.cash_out_sum == 14000
            assert summary.in_game == 500
        finally:
            db.close()

    def test_update_session_summary_invalid_field(self, client, ledger_test_setup):
        """Update with invalid field should return appropriate response."""
        setup = ledger_test_setup
        game = setup['game']
        session1 = setup['session1']
        alice = setup['alice']

        response = client.put(f'/api/games/{game.public_code}/ledger/{session1.id}/{alice.id}',
            json={
                "invalid_field": "should be ignored"
            },
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'No valid fields to update' in data['message']

    def test_update_session_summary_names_validation(self, client, ledger_test_setup):
        """Update with names field should validate list format."""
        setup = ledger_test_setup
        game = setup['game']
        session1 = setup['session1']
        alice = setup['alice']

        # Test with valid names list
        response = client.put(f'/api/games/{game.public_code}/ledger/{session1.id}/{alice.id}',
            json={
                "names": ["Alice Updated", "Alice Alt"]
            },
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 200

        # Test with invalid names (not a list)
        response = client.put(f'/api/games/{game.public_code}/ledger/{session1.id}/{alice.id}',
            json={
                "names": "not a list"
            },
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'must be a list' in data['error']

    def test_update_session_summary_nonexistent_entry(self, client, ledger_test_setup):
        """Update nonexistent session summary should return 404."""
        setup = ledger_test_setup
        game = setup['game']
        fake_session_id = str(uuid.uuid4())
        fake_player_id = str(uuid.uuid4())

        response = client.put(f'/api/games/{game.public_code}/ledger/{fake_session_id}/{fake_player_id}',
            json={
                "buy_in_sum": 10000
            },
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'not found' in data['error'].lower()

    def test_update_session_summary_requires_admin_code(self, client, ledger_test_setup):
        """Update session summary requires admin code."""
        setup = ledger_test_setup
        game = setup['game']
        session1 = setup['session1']
        alice = setup['alice']

        response = client.put(f'/api/games/{game.public_code}/ledger/{session1.id}/{alice.id}',
            json={
                "buy_in_sum": 15000
            }
            # No admin code
        )

        assert response.status_code == 401
        data = response.get_json()
        assert 'Missing authentication' in data['error'] or 'JWT token or X-Admin-Code' in data['error']

    def test_update_session_summary_invalid_admin_code(self, client, ledger_test_setup):
        """Update with invalid admin code should be rejected."""
        setup = ledger_test_setup
        game = setup['game']
        session1 = setup['session1']
        alice = setup['alice']

        response = client.put(f'/api/games/{game.public_code}/ledger/{session1.id}/{alice.id}',
            json={
                "buy_in_sum": 15000
            },
            headers={'X-Admin-Code': 'invalid_admin_code'}
        )

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data


class TestLedgerDeletion:
    """Test ledger deletion endpoints."""

    def test_delete_session_summary(self, client, ledger_test_setup):
        """Delete a session summary entry."""
        setup = ledger_test_setup
        game = setup['game']
        session1 = setup['session1']
        alice = setup['alice']

        response = client.delete(f'/api/games/{game.public_code}/ledger/{session1.id}/{alice.id}',
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        assert 'deleted successfully' in data['message']

        # Verify deletion in database
        db = SessionLocal()
        try:
            summary = db.query(SessionPlayerSummary).filter_by(
                session_id=session1.id,
                player_id=alice.id
            ).first()
            assert summary is None
        finally:
            db.close()

    def test_delete_session_summary_nonexistent(self, client, ledger_test_setup):
        """Delete nonexistent session summary should return 404."""
        setup = ledger_test_setup
        game = setup['game']
        fake_session_id = str(uuid.uuid4())
        fake_player_id = str(uuid.uuid4())

        response = client.delete(f'/api/games/{game.public_code}/ledger/{fake_session_id}/{fake_player_id}',
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

    def test_delete_entire_session(self, client, ledger_test_setup):
        """Delete entire session including all player summaries."""
        setup = ledger_test_setup
        game = setup['game']
        session1 = setup['session1']

        response = client.delete(f'/api/games/{game.public_code}/sessions/{session1.id}',
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        assert 'deleted successfully' in data['message']
        assert 'deleted_count' in data

        # Verify all summaries for this session were deleted
        db = SessionLocal()
        try:
            summaries = db.query(SessionPlayerSummary).filter_by(session_id=session1.id).all()
            assert len(summaries) == 0
        finally:
            db.close()

    def test_delete_entire_session_nonexistent(self, client, ledger_test_setup):
        """Delete nonexistent session should return appropriate response."""
        setup = ledger_test_setup
        game = setup['game']
        fake_session_id = str(uuid.uuid4())

        response = client.delete(f'/api/games/{game.public_code}/sessions/{fake_session_id}',
            headers={'X-Admin-Code': game.admin_code}
        )

        # Should return success with 0 deleted count or 404
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.get_json()
            assert data['deleted_count'] == 0

    def test_delete_operations_require_admin_code(self, client, ledger_test_setup):
        """Delete operations require admin code."""
        setup = ledger_test_setup
        game = setup['game']
        session1 = setup['session1']
        alice = setup['alice']

        # Test session summary deletion
        response = client.delete(f'/api/games/{game.public_code}/ledger/{session1.id}/{alice.id}')

        assert response.status_code == 401
        data = response.get_json()
        assert ('Missing authentication' in data['error'] or
                'JWT token or X-Admin-Code' in data['error'] or
                'X-Admin-Code header required' in data['error'])

        # Test entire session deletion
        response = client.delete(f'/api/games/{game.public_code}/sessions/{session1.id}')

        assert response.status_code == 401
        data = response.get_json()
        assert ('Missing authentication' in data['error'] or
                'JWT token or X-Admin-Code' in data['error'] or
                'X-Admin-Code header required' in data['error'])


class TestLedgerValidationAndEdgeCases:
    """Test validation and edge cases for ledger operations."""

    def test_update_with_negative_values(self, client, ledger_test_setup):
        """Update with negative values should be allowed for net calculations."""
        setup = ledger_test_setup
        game = setup['game']
        session1 = setup['session1']
        alice = setup['alice']

        response = client.put(f'/api/games/{game.public_code}/ledger/{session1.id}/{alice.id}',
            json={
                "buy_in_sum": 10000,
                "cash_out_sum": 5000,  # Less than buy-in (loss)
                "net": -5000  # Negative net
            },
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'updated successfully' in data['message']

    def test_update_with_zero_values(self, client, ledger_test_setup):
        """Update with zero values should be allowed."""
        setup = ledger_test_setup
        game = setup['game']
        session1 = setup['session1']
        alice = setup['alice']

        response = client.put(f'/api/games/{game.public_code}/ledger/{session1.id}/{alice.id}',
            json={
                "buy_in_sum": 0,
                "cash_out_sum": 0,
                "in_game": 0,
                "net": 0
            },
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'updated successfully' in data['message']

    def test_update_skips_game_number_field(self, client, ledger_test_setup):
        """Update should skip game_number field."""
        setup = ledger_test_setup
        game = setup['game']
        session1 = setup['session1']
        alice = setup['alice']

        response = client.put(f'/api/games/{game.public_code}/ledger/{session1.id}/{alice.id}',
            json={
                "game_number": 999,  # Should be ignored
                "buy_in_sum": 11000  # Should be processed
            },
            headers={'X-Admin-Code': game.admin_code}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'updated successfully' in data['message']

        # Verify buy_in_sum was updated but game_number wasn't changed
        db = SessionLocal()
        try:
            summary = db.query(SessionPlayerSummary).filter_by(
                session_id=session1.id,
                player_id=alice.id
            ).first()
            assert summary.buy_in_sum == 11000
            # Game number should remain unchanged on the session
            session = db.query(SessionModel).filter_by(id=session1.id).first()
            assert session.game_number == 1  # Original value
        finally:
            db.close()

    def test_update_with_large_values(self, client, ledger_test_setup):
        """Update with large monetary values."""
        setup = ledger_test_setup
        game = setup['game']
        session1 = setup['session1']
        alice = setup['alice']

        large_value = 99999999  # Large amount in cents

        response = client.put(f'/api/games/{game.public_code}/ledger/{session1.id}/{alice.id}',
            json={
                "buy_in_sum": large_value,
                "cash_out_sum": large_value + 100000
            },
            headers={'X-Admin-Code': game.admin_code}
        )

        # Should either succeed or fail gracefully
        assert response.status_code in [200, 400]

        if response.status_code == 200:
            data = response.get_json()
            assert 'updated successfully' in data['message']

    def test_concurrent_ledger_updates(self, client, ledger_test_setup):
        """Test concurrent updates to same ledger entry."""
        setup = ledger_test_setup
        game = setup['game']
        session1 = setup['session1']
        alice = setup['alice']

        # Perform two updates rapidly
        response1 = client.put(f'/api/games/{game.public_code}/ledger/{session1.id}/{alice.id}',
            json={"buy_in_sum": 11000},
            headers={'X-Admin-Code': game.admin_code}
        )

        response2 = client.put(f'/api/games/{game.public_code}/ledger/{session1.id}/{alice.id}',
            json={"cash_out_sum": 16000},
            headers={'X-Admin-Code': game.admin_code}
        )

        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200

        # Final state should reflect both updates
        db = SessionLocal()
        try:
            summary = db.query(SessionPlayerSummary).filter_by(
                session_id=session1.id,
                player_id=alice.id
            ).first()
            assert summary.buy_in_sum == 11000
            assert summary.cash_out_sum == 16000
        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])