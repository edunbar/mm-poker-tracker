"""
Integration tests for game claiming functionality.

Tests the POST /api/games/claim endpoint covering all scenarios:
- New claim (201)
- Re-claim by owner (200)
- Already claimed by different user (409)
- Invalid admin code (403)
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from db.database import engine
from db.models import Game


class TestGameClaiming:
    """Test suite for game claiming endpoint."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clean database before and after each test."""
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM audit_log CASCADE"))
            conn.execute(text("DELETE FROM games CASCADE"))
            conn.execute(text("DELETE FROM users CASCADE"))
            conn.commit()

        yield

        with engine.connect() as conn:
            conn.execute(text("DELETE FROM audit_log CASCADE"))
            conn.execute(text("DELETE FROM games CASCADE"))
            conn.execute(text("DELETE FROM users CASCADE"))
            conn.commit()

    def test_claim_game_success(self, test_client, register_user, create_game, db_session):
        """Test successfully claiming an unclaimed game."""
        # Register user
        user, token = register_user('claimer@example.com', 'SecurePassword123!')

        # Create unclaimed game
        game = create_game()

        # Claim the game
        response = test_client.post('/api/games/claim',
            headers={'Authorization': f'Bearer {token}'},
            json={'admin_code': game.admin_code}
        )

        assert response.status_code == 201
        data = response.get_json()

        # Verify response structure
        assert data['message'] == 'Game successfully claimed'
        assert 'game' in data
        assert data['game']['id'] == str(game.id)
        assert data['game']['public_code'] == game.public_code
        assert 'claimed_at' in data['game']
        assert 'admin_code_expires_at' in data['game']

        # Verify database changes
        db_session.refresh(game)
        assert game.owner_user_id is not None
        assert str(game.owner_user_id) == user['id']
        assert game.admin_code_expires_at is not None

        # Verify expiration is ~90 days from now
        expires_at = game.admin_code_expires_at
        now = datetime.now(timezone.utc)
        expected_expiration = now + timedelta(days=90)
        time_diff = abs((expires_at - expected_expiration).total_seconds())
        assert time_diff < 60  # Within 1 minute

    def test_claim_game_already_owned_by_self(self, test_client, register_user, create_game, db_session):
        """Test re-claiming extends expiration - should return 200."""
        # Register user
        user, token = register_user('reclaimer@example.com', 'SecurePassword123!')

        # Create and claim game
        game = create_game()
        test_client.post('/api/games/claim',
            headers={'Authorization': f'Bearer {token}'},
            json={'admin_code': game.admin_code}
        )

        # Get original expiration
        db_session.refresh(game)
        original_expiration = game.admin_code_expires_at

        # Wait a moment and re-claim
        import time
        time.sleep(1)

        response = test_client.post('/api/games/claim',
            headers={'Authorization': f'Bearer {token}'},
            json={'admin_code': game.admin_code}
        )

        assert response.status_code == 200  # Not 201
        data = response.get_json()

        # Verify response message
        assert 'expiration extended' in data['message'].lower()
        assert 'game' in data
        assert 'admin_code_expires_at' in data['game']

        # Verify expiration was extended
        db_session.refresh(game)
        new_expiration = game.admin_code_expires_at
        assert new_expiration > original_expiration

    def test_claim_game_owned_by_other_user(self, test_client, register_user, create_game):
        """Test trying to claim someone else's game - should return 409."""
        # Register first user and claim game
        user1, token1 = register_user('owner@example.com', 'SecurePassword123!')
        game = create_game()
        test_client.post('/api/games/claim',
            headers={'Authorization': f'Bearer {token1}'},
            json={'admin_code': game.admin_code}
        )

        # Register second user
        user2, token2 = register_user('thief@example.com', 'SecurePassword123!')

        # Try to claim with second user's token
        response = test_client.post('/api/games/claim',
            headers={'Authorization': f'Bearer {token2}'},
            json={'admin_code': game.admin_code}
        )

        assert response.status_code == 409
        data = response.get_json()
        assert 'error' in data
        assert 'already claimed by another user' in data['error'].lower()

    def test_claim_game_invalid_admin_code(self, test_client, register_user):
        """Test trying to claim with wrong admin code - should return 403."""
        # Register user
        user, token = register_user('hacker@example.com', 'SecurePassword123!')

        # Try to claim with invalid admin code
        response = test_client.post('/api/games/claim',
            headers={'Authorization': f'Bearer {token}'},
            json={'admin_code': 'wrong-admin-code-12345'}
        )

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data
        assert 'invalid admin code' in data['error'].lower()
