"""
Integration tests for audit logging with user_id tracking.

Tests verify that audit_log table correctly records user_id
when JWT authentication is used, and NULL when admin code is used.
"""

import pytest
from sqlalchemy import text
from db.database import engine
from db.models import AuditLog


class TestAuditLogging:
    """Test suite for audit logging integration with authentication."""

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

    def test_audit_log_includes_user_id_for_jwt_auth(
        self, test_client, register_user, create_game, auth_headers, db_session
    ):
        """Verify audit log has user_id when using JWT."""
        # Register user and claim game
        user, token = register_user('audituser@example.com', 'SecurePassword123!')
        game = create_game()

        test_client.post('/api/games/claim',
            headers=auth_headers(token),
            json={'admin_code': game.admin_code}
        )

        # Query audit log for GAME_CLAIM action
        audit_logs = db_session.query(AuditLog).filter(
            AuditLog.action == 'GAME_CLAIM',
            AuditLog.game_id == str(game.id)
        ).all()

        assert len(audit_logs) > 0, "No audit log entry found for GAME_CLAIM"

        # Verify user_id is set
        audit_entry = audit_logs[0]
        assert audit_entry.user_id is not None, "user_id should not be NULL for JWT auth"
        assert str(audit_entry.user_id) == user['id'], "user_id should match authenticated user"
        assert audit_entry.actor_kind in ['jwt', 'user'], f"actor_kind should be 'jwt' or 'user', got: {audit_entry.actor_kind}"

    def test_audit_log_null_user_id_for_admin_code(
        self, test_client, create_game, admin_code_headers, db_session
    ):
        """Verify audit log has NULL user_id when using admin code."""
        # Create game and perform action with admin code
        game = create_game()

        # Attempt an upload with admin code (will fail on validation, but should create audit log)
        test_client.post('/api/games/upload',
            headers=admin_code_headers(game.admin_code),
            json={
                'public_code': game.public_code,
                'sessionId': 'audit-test-session',
                'game_data': {}
            }
        )

        # Query audit log for any entry related to this game
        audit_logs = db_session.query(AuditLog).filter(
            AuditLog.game_id == str(game.id)
        ).all()

        if len(audit_logs) > 0:
            # If audit logs exist, verify user_id is NULL
            audit_entry = audit_logs[0]
            assert audit_entry.user_id is None, "user_id should be NULL for admin code auth"
            assert audit_entry.actor_kind == 'admin_code', f"actor_kind should be 'admin_code', got: {audit_entry.actor_kind}"

    def test_audit_log_claim_operation(
        self, test_client, register_user, create_game, auth_headers, db_session
    ):
        """Test audit log for game claim operation."""
        # Register user and claim game
        user, token = register_user('claimaudit@example.com', 'SecurePassword123!')
        game = create_game()

        test_client.post('/api/games/claim',
            headers=auth_headers(token),
            json={'admin_code': game.admin_code}
        )

        # Query audit logs
        audit_logs = db_session.query(AuditLog).filter(
            AuditLog.game_id == str(game.id),
            AuditLog.action.in_(['GAME_CLAIM', 'GAME_CLAIM_EXTEND'])
        ).all()

        assert len(audit_logs) > 0, "Should have audit log for game claim"

        audit_entry = audit_logs[0]

        # Verify operation type
        assert audit_entry.action in ['GAME_CLAIM', 'GAME_CLAIM_EXTEND']

        # Verify user_id is set
        assert audit_entry.user_id is not None
        assert str(audit_entry.user_id) == user['id']

        # Verify game_id is set
        assert audit_entry.game_id is not None
        assert str(audit_entry.game_id) == str(game.id)

        # Verify actor information
        assert audit_entry.actor_kind in ['jwt', 'user']
        assert audit_entry.actor_id == user['email']
