"""
Integration tests for dual authentication on game routes.

Tests verify that protected game routes accept both JWT authentication
(for game owners) and X-Admin-Code authentication (backward compatibility),
with proper authorization checks and admin code expiration.
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from db.database import engine


class TestAuthGameIntegration:
    """Test suite for dual authentication on protected game routes."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clean database before and after each test."""
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM audit_log CASCADE"))
            conn.execute(text("DELETE FROM payment_transactions CASCADE"))
            conn.execute(text("DELETE FROM payment_balances CASCADE"))
            conn.execute(text("DELETE FROM session_player_summaries CASCADE"))
            conn.execute(text("DELETE FROM sessions CASCADE"))
            conn.execute(text("DELETE FROM game_players CASCADE"))
            conn.execute(text("DELETE FROM players CASCADE"))
            conn.execute(text("DELETE FROM games CASCADE"))
            conn.execute(text("DELETE FROM users CASCADE"))
            conn.commit()

        yield

        with engine.connect() as conn:
            conn.execute(text("DELETE FROM audit_log CASCADE"))
            conn.execute(text("DELETE FROM payment_transactions CASCADE"))
            conn.execute(text("DELETE FROM payment_balances CASCADE"))
            conn.execute(text("DELETE FROM session_player_summaries CASCADE"))
            conn.execute(text("DELETE FROM sessions CASCADE"))
            conn.execute(text("DELETE FROM game_players CASCADE"))
            conn.execute(text("DELETE FROM players CASCADE"))
            conn.execute(text("DELETE FROM games CASCADE"))
            conn.execute(text("DELETE FROM users CASCADE"))
            conn.commit()

    # ========================================================================
    # Session Upload Tests (4)
    # ========================================================================

    def test_session_upload_with_jwt_auth(self, test_client, register_user, create_game, auth_headers):
        """Test uploading session with JWT instead of admin code."""
        # Register user and create game
        user, token = register_user('uploader@example.com', 'SecurePassword123!')
        game = create_game()

        # Claim the game
        test_client.post('/api/games/claim',
            headers=auth_headers(token),
            json={'admin_code': game.admin_code}
        )

        # Upload session with JWT
        response = test_client.post('/api/games/upload',
            headers=auth_headers(token),
            json={
                'public_code': game.public_code,
                'sessionId': 'test-session-001',
                'game_data': {}
            }
        )

        # Auth should pass, may fail on business logic (empty game_data)
        # Either 200 (success) or 400 (validation error) is acceptable
        assert response.status_code in [200, 400]

        # If 400, verify it's NOT an auth error
        if response.status_code == 400:
            data = response.get_json()
            assert 'not authorized' not in data.get('error', '').lower()
            assert 'missing auth' not in data.get('error', '').lower()

    def test_session_upload_with_admin_code_still_works(self, test_client, create_game, admin_code_headers):
        """Test backward compatibility - admin codes still work."""
        # Create unclaimed game
        game = create_game()

        # Upload with admin code (old way)
        response = test_client.post('/api/games/upload',
            headers=admin_code_headers(game.admin_code),
            json={
                'public_code': game.public_code,
                'sessionId': 'test-session-002',
                'game_data': {}
            }
        )

        # Auth should pass
        assert response.status_code in [200, 400]

        if response.status_code == 400:
            data = response.get_json()
            assert 'not authorized' not in data.get('error', '').lower()

    def test_session_upload_jwt_wrong_game_owner(self, test_client, register_user, create_game, auth_headers):
        """Test JWT auth but user doesn't own the game - should 403."""
        # User A creates and claims game
        user_a, token_a = register_user('owner@example.com', 'SecurePassword123!')
        game = create_game()
        test_client.post('/api/games/claim',
            headers=auth_headers(token_a),
            json={'admin_code': game.admin_code}
        )

        # User B tries to upload
        user_b, token_b = register_user('intruder@example.com', 'SecurePassword123!')
        response = test_client.post('/api/games/upload',
            headers=auth_headers(token_b),
            json={
                'public_code': game.public_code,
                'sessionId': 'test-session-003',
                'game_data': {}
            }
        )

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data
        assert 'not authorized' in data['error'].lower() or 'do not own' in data['error'].lower()

    def test_session_upload_admin_code_expired(self, test_client, register_user, create_game, admin_code_headers, db_session):
        """Test admin code after 90-day expiration - should fail."""
        # Register a user and get their ID
        user, token = register_user('expiredowner@example.com', 'SecurePassword123!')

        # Create and artificially claim game with expired admin code
        game = create_game(owner_id=user['id'])
        game.admin_code_expires_at = datetime.now(timezone.utc) - timedelta(days=1)  # Expired
        db_session.commit()

        # Try to upload with expired admin code
        response = test_client.post('/api/games/upload',
            headers=admin_code_headers(game.admin_code),
            json={
                'public_code': game.public_code,
                'sessionId': 'test-session-004',
                'game_data': {}
            }
        )

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data
        assert 'expired' in data['error'].lower()

    # ========================================================================
    # Payment Route Tests (4)
    # ========================================================================

    def test_payment_with_jwt_auth(self, test_client, register_user, create_game, auth_headers):
        """Test POST /payments with JWT works."""
        # Setup
        user, token = register_user('payer@example.com', 'SecurePassword123!')
        game = create_game()
        test_client.post('/api/games/claim',
            headers=auth_headers(token),
            json={'admin_code': game.admin_code}
        )

        # Record payment with JWT
        response = test_client.post(f'/api/games/{game.public_code}/payments',
            headers=auth_headers(token),
            json={
                'payer_id': '00000000-0000-0000-0000-000000000001',
                'recipient_id': '00000000-0000-0000-0000-000000000002',
                'amount': 50.00
            }
        )

        # Auth passes, may fail on player validation
        assert response.status_code in [201, 400]

        if response.status_code == 400:
            data = response.get_json()
            assert 'not authorized' not in data.get('error', '').lower()

    def test_payment_with_admin_code(self, test_client, create_game, admin_code_headers):
        """Test POST /payments with X-Admin-Code works."""
        game = create_game()

        response = test_client.post(f'/api/games/{game.public_code}/payments',
            headers=admin_code_headers(game.admin_code),
            json={
                'payer_id': '00000000-0000-0000-0000-000000000001',
                'recipient_id': '00000000-0000-0000-0000-000000000002',
                'amount': 75.00
            }
        )

        assert response.status_code in [201, 400]

    def test_payment_jwt_not_owner(self, test_client, register_user, create_game, auth_headers):
        """Test different user JWT fails with 403."""
        # User A owns game
        user_a, token_a = register_user('gameowner@example.com', 'SecurePassword123!')
        game = create_game()
        test_client.post('/api/games/claim',
            headers=auth_headers(token_a),
            json={'admin_code': game.admin_code}
        )

        # User B tries to record payment
        user_b, token_b = register_user('other@example.com', 'SecurePassword123!')
        response = test_client.post(f'/api/games/{game.public_code}/payments',
            headers=auth_headers(token_b),
            json={
                'payer_id': '00000000-0000-0000-0000-000000000001',
                'recipient_id': '00000000-0000-0000-0000-000000000002',
                'amount': 25.00
            }
        )

        assert response.status_code == 403
        data = response.get_json()
        assert 'not authorized' in data['error'].lower()

    def test_payment_no_auth(self, test_client, create_game):
        """Test no auth header fails with 401."""
        game = create_game()

        response = test_client.post(f'/api/games/{game.public_code}/payments',
            json={
                'payer_id': '00000000-0000-0000-0000-000000000001',
                'recipient_id': '00000000-0000-0000-0000-000000000002',
                'amount': 30.00
            }
        )

        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
        assert 'missing authentication' in data['error'].lower() or 'authorization' in data['error'].lower()

    # ========================================================================
    # Ledger Route Tests (4)
    # ========================================================================

    def test_ledger_update_with_jwt(self, test_client, register_user, create_game, auth_headers):
        """Test PUT /ledger/<session>/<player> with JWT."""
        # Setup
        user, token = register_user('ledgeruser@example.com', 'SecurePassword123!')
        game = create_game()
        test_client.post('/api/games/claim',
            headers=auth_headers(token),
            json={'admin_code': game.admin_code}
        )

        # Update ledger with JWT
        response = test_client.put(f'/api/games/{game.public_code}/ledger/session-123/player-456',
            headers=auth_headers(token),
            json={
                'buy_in_sum': 10000,
                'cash_out_sum': 12000,
                'in_game': 0,
                'net': 2000,
                'names': ['Test Player']
            }
        )

        # Auth passes, may fail on session/player validation
        assert response.status_code in [200, 400, 404]

        if response.status_code in [400, 404]:
            data = response.get_json()
            assert 'not authorized' not in data.get('error', '').lower()

    def test_ledger_update_with_admin_code(self, test_client, create_game, admin_code_headers):
        """Test PUT /ledger with X-Admin-Code."""
        game = create_game()

        response = test_client.put(f'/api/games/{game.public_code}/ledger/session-789/player-012',
            headers=admin_code_headers(game.admin_code),
            json={
                'buy_in_sum': 5000,
                'cash_out_sum': 6000,
                'in_game': 0,
                'net': 1000,
                'names': ['Another Player']
            }
        )

        assert response.status_code in [200, 400, 404]

    def test_ledger_delete_with_jwt(self, test_client, register_user, create_game, auth_headers):
        """Test DELETE /ledger/<session>/<player> with JWT."""
        # Setup
        user, token = register_user('deleteuser@example.com', 'SecurePassword123!')
        game = create_game()
        test_client.post('/api/games/claim',
            headers=auth_headers(token),
            json={'admin_code': game.admin_code}
        )

        # Delete ledger entry with JWT
        response = test_client.delete(f'/api/games/{game.public_code}/ledger/session-999/player-888',
            headers=auth_headers(token)
        )

        # Auth passes, may fail on finding entry
        assert response.status_code in [200, 404]

        if response.status_code == 404:
            data = response.get_json()
            assert 'not authorized' not in data.get('error', '').lower()

    def test_ledger_delete_wrong_owner(self, test_client, register_user, create_game, auth_headers):
        """Test DELETE with non-owner JWT fails 403."""
        # User A owns game
        user_a, token_a = register_user('ledgerowner@example.com', 'SecurePassword123!')
        game = create_game()
        test_client.post('/api/games/claim',
            headers=auth_headers(token_a),
            json={'admin_code': game.admin_code}
        )

        # User B tries to delete
        user_b, token_b = register_user('wronguser@example.com', 'SecurePassword123!')
        response = test_client.delete(f'/api/games/{game.public_code}/ledger/session-111/player-222',
            headers=auth_headers(token_b)
        )

        assert response.status_code == 403
        data = response.get_json()
        assert 'not authorized' in data['error'].lower()
