"""
Authentication & Authorization Integration Tests

Tests admin code validation and security across all API endpoints.
Ensures proper isolation between games and correct access control.
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
def test_games():
    """Create multiple test games with different admin codes."""
    db = SessionLocal()
    try:
        # Create two games with different admin codes
        unique_id_1 = str(uuid.uuid4())[:8].upper()
        unique_id_2 = str(uuid.uuid4())[:8].upper()

        game1 = Game(
            public_code=f"G1{unique_id_1}",  # Use full unique_id to avoid collisions
            admin_code=f"admin_code_game1_{unique_id_1}",  # Long admin code
            title=f"Test Game 1 {unique_id_1}"
        )

        game2 = Game(
            public_code=f"G2{unique_id_2}",  # Use full unique_id to avoid collisions
            admin_code=f"admin_code_game2_{unique_id_2}",  # Different admin code
            title=f"Test Game 2 {unique_id_2}"
        )

        db.add_all([game1, game2])
        db.flush()

        # Create a player for each game
        player1 = Player(
            display_name=f"Player1_{unique_id_1}",
            external_id=f"ext_player1_{unique_id_1}"
        )
        player2 = Player(
            display_name=f"Player2_{unique_id_2}",
            external_id=f"ext_player2_{unique_id_2}"
        )

        db.add_all([player1, player2])
        db.flush()

        # Create sessions for each game
        session1 = SessionModel(
            game_id=game1.id,
            external_id=f"test_session_1_{unique_id_1}",
            session_type="test",
            game_number=1
        )
        session2 = SessionModel(
            game_id=game2.id,
            external_id=f"test_session_2_{unique_id_2}",
            session_type="test",
            game_number=1
        )

        db.add_all([session1, session2])
        db.flush()

        # Create session summaries
        summary1 = SessionPlayerSummary(
            session_id=session1.id,
            player_id=player1.id,
            buy_in_sum=10000,
            cash_out_sum=15000,
            in_game=0,
            net=5000,
            names=[player1.display_name]
        )
        summary2 = SessionPlayerSummary(
            session_id=session2.id,
            player_id=player2.id,
            buy_in_sum=10000,
            cash_out_sum=8000,
            in_game=0,
            net=-2000,
            names=[player2.display_name]
        )

        db.add_all([summary1, summary2])
        db.commit()

        yield {
            'game1': game1,
            'game2': game2,
            'player1': player1,
            'player2': player2,
            'session1': session1,
            'session2': session2
        }

    finally:
        db.close()


class TestAdminCodeValidation:
    """Test admin code validation across all endpoints."""

    def test_session_upload_valid_admin_code(self, client, test_games):
        """Valid admin code allows session upload."""
        game1 = test_games['game1']

        response = client.post('/api/games/upload',
            json={
                "public_code": game1.public_code,
                "sessionId": "test_session_auth_123",
                "game_data": {
                    "playersInfos": {
                        "player1": {
                            "id": "player1",
                            "name": "Alice",
                            "buyInSum": 10000,
                            "buyOutSum": 15000,
                            "net": 5000
                        }
                    }
                }
            },
            headers={'X-Admin-Code': game1.admin_code}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_session_upload_invalid_admin_code(self, client, test_games):
        """Invalid admin code rejects session upload."""
        game1 = test_games['game1']

        response = client.post('/api/games/upload',
            json={
                "public_code": game1.public_code,
                "sessionId": "test_session_auth_456",
                "game_data": {
                    "playersInfos": {
                        "player1": {
                            "id": "player1",
                            "name": "Alice",
                            "buyInSum": 10000,
                            "buyOutSum": 15000,
                            "net": 5000
                        }
                    }
                }
            },
            headers={'X-Admin-Code': 'invalid_admin_code'}
        )

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data
        assert 'admin code' in data['error'].lower()

    def test_session_upload_missing_admin_code(self, client, test_games):
        """Missing admin code header is rejected."""
        game1 = test_games['game1']

        response = client.post('/api/games/upload',
            json={
                "public_code": game1.public_code,
                "sessionId": "test_session_auth_789",
                "game_data": {
                    "playersInfos": {
                        "player1": {
                            "id": "player1",
                            "name": "Alice",
                            "buyInSum": 10000,
                            "buyOutSum": 15000,
                            "net": 5000
                        }
                    }
                }
            }
            # No X-Admin-Code header
        )

        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
        assert 'Missing authentication' in data['error'] or 'JWT token or X-Admin-Code' in data['error']

    def test_ledger_update_valid_admin_code(self, client, test_games):
        """Valid admin code allows ledger updates."""
        game1 = test_games['game1']
        session1 = test_games['session1']
        player1 = test_games['player1']

        response = client.put(f'/api/games/{game1.public_code}/ledger/{session1.id}/{player1.id}',
            json={
                "buy_in_sum": 12000,
                "notes": "Updated via API test"
            },
            headers={'X-Admin-Code': game1.admin_code}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'updated successfully' in data['message']

    def test_ledger_update_invalid_admin_code(self, client, test_games):
        """Invalid admin code rejects ledger updates."""
        game1 = test_games['game1']
        session1 = test_games['session1']
        player1 = test_games['player1']

        response = client.put(f'/api/games/{game1.public_code}/ledger/{session1.id}/{player1.id}',
            json={
                "buy_in_sum": 12000,
                "notes": "Should be rejected"
            },
            headers={'X-Admin-Code': 'wrong_admin_code'}
        )

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data

    def test_ledger_delete_valid_admin_code(self, client, test_games):
        """Valid admin code allows ledger deletion."""
        game1 = test_games['game1']
        session1 = test_games['session1']
        player1 = test_games['player1']

        response = client.delete(f'/api/games/{game1.public_code}/ledger/{session1.id}/{player1.id}',
            headers={'X-Admin-Code': game1.admin_code}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'deleted successfully' in data['message']

    def test_session_delete_invalid_admin_code(self, client, test_games):
        """Invalid admin code rejects session deletion."""
        game1 = test_games['game1']
        session1 = test_games['session1']

        response = client.delete(f'/api/games/{game1.public_code}/sessions/{session1.id}',
            headers={'X-Admin-Code': 'wrong_admin_code'}
        )

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data

    def test_payment_record_missing_admin_code(self, client, test_games):
        """Payment recording requires admin code."""
        game1 = test_games['game1']
        player1 = test_games['player1']

        # Create a second player for the payment
        db = SessionLocal()
        try:
            import uuid
            unique_id = str(uuid.uuid4())[:8]
            player2 = Player(
                display_name=f"Test Player 2 {unique_id}",
                external_id=f"test_player_2_payment_{unique_id}"
            )
            db.add(player2)
            db.commit()

            response = client.post(f'/api/games/{game1.public_code}/payments',
                json={
                    "payer_id": str(player1.id),
                    "recipient_id": str(player2.id),
                    "amount": 50.00,
                    "payment_method": "test"
                }
                # No X-Admin-Code header
            )

            assert response.status_code == 401
            data = response.get_json()
            assert 'Missing authentication' in data['error'] or 'JWT token or X-Admin-Code' in data['error']

        finally:
            db.close()


class TestCrossGameAccessControl:
    """Test that admin codes are properly isolated between games."""

    def test_cross_game_admin_code_rejection(self, client, test_games):
        """Admin code from game1 should not work for game2."""
        game1 = test_games['game1']
        game2 = test_games['game2']

        # Try to upload to game2 using game1's admin code
        response = client.post('/api/games/upload',
            json={
                "public_code": game2.public_code,  # Game 2's public code
                "sessionId": "cross_game_test_123",
                "game_data": {
                    "playersInfos": {
                        "player1": {
                            "id": "player1",
                            "name": "Alice",
                            "buyInSum": 10000,
                            "buyOutSum": 15000,
                            "net": 5000
                        }
                    }
                }
            },
            headers={'X-Admin-Code': game1.admin_code}  # Game 1's admin code
        )

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data
        assert 'admin code' in data['error'].lower()

    def test_cross_game_ledger_access_denied(self, client, test_games):
        """Cannot access game2's ledger with game1's admin code."""
        game1 = test_games['game1']
        game2 = test_games['game2']
        session2 = test_games['session2']
        player2 = test_games['player2']

        response = client.put(f'/api/games/{game2.public_code}/ledger/{session2.id}/{player2.id}',
            json={
                "buy_in_sum": 15000,
                "notes": "Cross-game access attempt"
            },
            headers={'X-Admin-Code': game1.admin_code}  # Wrong game's admin code
        )

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data

    def test_cross_game_session_deletion_denied(self, client, test_games):
        """Cannot delete game2's session with game1's admin code."""
        game1 = test_games['game1']
        game2 = test_games['game2']
        session2 = test_games['session2']

        response = client.delete(f'/api/games/{game2.public_code}/sessions/{session2.id}',
            headers={'X-Admin-Code': game1.admin_code}  # Wrong game's admin code
        )

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data


class TestPublicVsAdminOperations:
    """Test that public codes allow read operations but admin codes are required for writes."""

    def test_public_code_allows_summary_read(self, client, test_games):
        """Public code should allow reading game summaries."""
        game1 = test_games['game1']

        response = client.get(f'/api/games/{game1.public_code}/summary')

        assert response.status_code == 200
        data = response.get_json()
        assert 'title' in data
        assert 'rows' in data

    def test_public_code_allows_analytics_read(self, client, test_games):
        """Public code should allow reading game analytics."""
        game1 = test_games['game1']

        response = client.get(f'/api/games/{game1.public_code}/analytics')

        assert response.status_code == 200
        data = response.get_json()
        assert 'analytics' in data

    def test_public_code_allows_payments_read(self, client, test_games):
        """Public code should allow reading payment summaries."""
        game1 = test_games['game1']

        response = client.get(f'/api/games/{game1.public_code}/payments')

        assert response.status_code == 200
        data = response.get_json()
        # Should return payment summary (may be empty)
        assert isinstance(data, list)

    def test_admin_required_for_session_upload(self, client, test_games):
        """Session upload requires admin code, not just public code."""
        game1 = test_games['game1']

        # This test is already covered above but confirms the pattern
        response = client.post('/api/games/upload',
            json={
                "public_code": game1.public_code,
                "sessionId": "admin_required_test",
                "game_data": {
                    "playersInfos": {
                        "player1": {
                            "id": "player1",
                            "name": "Alice",
                            "buyInSum": 10000,
                            "buyOutSum": 15000,
                            "net": 5000
                        }
                    }
                }
            }
            # No admin code provided
        )

        assert response.status_code == 401
        data = response.get_json()
        assert 'Missing authentication' in data['error'] or 'JWT token or X-Admin-Code' in data['error']

    def test_admin_required_for_ledger_modifications(self, client, test_games):
        """Ledger modifications require admin code."""
        game1 = test_games['game1']
        session1 = test_games['session1']
        player1 = test_games['player1']

        response = client.put(f'/api/games/{game1.public_code}/ledger/{session1.id}/{player1.id}',
            json={
                "buy_in_sum": 20000,
                "notes": "Admin required test"
            }
            # No admin code provided
        )

        assert response.status_code == 401
        data = response.get_json()
        assert 'Missing authentication' in data['error'] or 'JWT token or X-Admin-Code' in data['error']


class TestAdminCodeFormats:
    """Test admin code format validation and edge cases."""

    def test_empty_admin_code_rejected(self, client, test_games):
        """Empty admin code header should be rejected."""
        game1 = test_games['game1']

        response = client.post('/api/games/upload',
            json={
                "public_code": game1.public_code,
                "sessionId": "empty_admin_test",
                "game_data": {
                    "playersInfos": {
                        "player1": {
                            "id": "player1",
                            "name": "Alice",
                            "buyInSum": 10000,
                            "buyOutSum": 15000,
                            "net": 5000
                        }
                    }
                }
            },
            headers={'X-Admin-Code': ''}  # Empty admin code
        )

        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data

    def test_whitespace_admin_code_rejected(self, client, test_games):
        """Whitespace-only admin code should be rejected."""
        game1 = test_games['game1']

        response = client.post('/api/games/upload',
            json={
                "public_code": game1.public_code,
                "sessionId": "whitespace_admin_test",
                "game_data": {
                    "playersInfos": {
                        "player1": {
                            "id": "player1",
                            "name": "Alice",
                            "buyInSum": 10000,
                            "buyOutSum": 15000,
                            "net": 5000
                        }
                    }
                }
            },
            headers={'X-Admin-Code': '   '}  # Whitespace admin code
        )

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data

    def test_case_sensitive_admin_code(self, client, test_games):
        """Admin codes should be case sensitive."""
        game1 = test_games['game1']

        # Try with uppercase version of admin code
        uppercase_admin = game1.admin_code.upper()

        response = client.post('/api/games/upload',
            json={
                "public_code": game1.public_code,
                "sessionId": "case_sensitive_test",
                "game_data": {
                    "playersInfos": {
                        "player1": {
                            "id": "player1",
                            "name": "Alice",
                            "buyInSum": 10000,
                            "buyOutSum": 15000,
                            "net": 5000
                        }
                    }
                }
            },
            headers={'X-Admin-Code': uppercase_admin}
        )

        # Should fail if admin codes are case sensitive
        if uppercase_admin != game1.admin_code:
            assert response.status_code == 403
            data = response.get_json()
            assert 'error' in data


class TestSecurityHeaders:
    """Test security-related header handling."""

    def test_sql_injection_in_admin_code(self, client, test_games):
        """SQL injection attempts in admin code should be safely handled."""
        game1 = test_games['game1']

        malicious_admin_code = "admin'; DROP TABLE games; --"

        response = client.post('/api/games/upload',
            json={
                "public_code": game1.public_code,
                "sessionId": "sql_injection_test",
                "game_data": {
                    "playersInfos": {
                        "player1": {
                            "id": "player1",
                            "name": "Alice",
                            "buyInSum": 10000,
                            "buyOutSum": 15000,
                            "net": 5000
                        }
                    }
                }
            },
            headers={'X-Admin-Code': malicious_admin_code}
        )

        # Should safely reject the malicious admin code
        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data

        # Verify the database is still intact by making a valid request
        valid_response = client.get(f'/api/games/{game1.public_code}/summary')
        assert valid_response.status_code == 200

    def test_xss_in_admin_code(self, client, test_games):
        """XSS attempts in admin code should be safely handled."""
        game1 = test_games['game1']

        xss_admin_code = "<script>alert('xss')</script>"

        response = client.post('/api/games/upload',
            json={
                "public_code": game1.public_code,
                "sessionId": "xss_test",
                "game_data": {
                    "playersInfos": {
                        "player1": {
                            "id": "player1",
                            "name": "Alice",
                            "buyInSum": 10000,
                            "buyOutSum": 15000,
                            "net": 5000
                        }
                    }
                }
            },
            headers={'X-Admin-Code': xss_admin_code}
        )

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data
        # Ensure no script tags are reflected in the response
        assert '<script>' not in str(data)


class TestPasswordSecurityAPIs:
    """Test password security API endpoints."""

    def test_password_change_success(self, client):
        """Test successful password change."""
        from tests.conftest import register_user as register_helper
        from sqlalchemy import text

        #Clean up first
        with SessionLocal() as db:
            db.execute(text("DELETE FROM users CASCADE"))
            db.commit()

        # Register user
        response = client.post('/api/auth/register', json={
            'email': 'pwtest@example.com',
            'password': 'OldPassword123!',
            'display_name': 'PW Test User'
        })
        token = response.get_json()['access_token']

        # Change password
        response = client.patch('/api/auth/password',
            headers={'Authorization': f'Bearer {token}'},
            json={
                'current_password': 'OldPassword123!',
                'new_password': 'NewPassword456!'
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        assert 'success' in data['message'].lower()

    def test_password_change_wrong_current_password(self, client):
        """Test password change with incorrect current password."""
        from sqlalchemy import text

        # Clean up
        with SessionLocal() as db:
            db.execute(text("DELETE FROM users CASCADE"))
            db.commit()

        # Register user
        response = client.post('/api/auth/register', json={
            'email': 'pwtest2@example.com',
            'password': 'CorrectPassword123!',
            'display_name': 'Test User'
        })
        token = response.get_json()['access_token']

        # Try with wrong current password
        response = client.patch('/api/auth/password',
            headers={'Authorization': f'Bearer {token}'},
            json={
                'current_password': 'WrongPassword123!',
                'new_password': 'NewPassword456!'
            }
        )

        assert response.status_code == 401
        data = response.get_json()
        assert 'incorrect' in data['error'].lower()

    def test_password_strength_check_strong(self, client):
        """Test password strength check with strong password."""
        response = client.post('/api/auth/password-strength', json={
            'password': 'MyVerySecurePassword123!'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert 'score' in data
        assert 'strength' in data
        assert 'feedback' in data
        assert data['score'] >= 80
        assert data['strength'] == 'strong'

    def test_password_strength_check_weak(self, client):
        """Test password strength check with weak password."""
        response = client.post('/api/auth/password-strength', json={
            'password': 'weak'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['score'] < 40
        assert data['strength'] == 'weak'
        assert len(data['feedback']) > 0

    def test_password_strength_common_password(self, client):
        """Test that common passwords are flagged."""
        response = client.post('/api/auth/password-strength', json={
            'password': 'password123'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['details']['is_common'] is True
        assert data['meets_requirements'] is False

    def test_password_requirements_endpoint(self, client):
        """Test password requirements endpoint."""
        response = client.get('/api/auth/password-requirements')

        assert response.status_code == 200
        data = response.get_json()
        assert 'min_length' in data
        assert 'max_length' in data
        assert 'requires_lowercase' in data
        assert 'requires_uppercase' in data
        assert 'requires_numbers' in data
        assert data['min_length'] == 8
        assert data['max_length'] == 72


if __name__ == "__main__":
    pytest.main([__file__, "-v"])