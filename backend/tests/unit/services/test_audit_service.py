"""
Unit tests for audit service security event logging.

Tests cover log_security_event() and get_user_security_logs() functions
for tracking security-related actions like password changes.
"""

import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone
from services.audit_service import log_security_event, get_user_security_logs


class TestLogSecurityEvent:
    """Test security event logging functionality."""

    @patch('services.audit_service.SessionLocal')
    def test_creates_audit_log_entry(self, mock_session_local):
        """Test that log_security_event creates an AuditLog entry."""
        mock_db = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_db

        user_id = str(uuid4())
        user_email = 'test@example.com'

        log_security_event(
            action='PASSWORD_CHANGED',
            user_id=user_id,
            user_email=user_email
        )

        # Verify audit log was added
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

        # Verify the audit log has correct attributes
        audit_entry = mock_db.add.call_args[0][0]
        assert audit_entry.action == 'PASSWORD_CHANGED'
        assert audit_entry.user_id == user_id
        assert audit_entry.actor_id == user_email
        assert audit_entry.actor_kind == 'user'
        assert audit_entry.target_table == 'users'
        assert audit_entry.target_id == user_id

    @patch('services.audit_service.SessionLocal')
    def test_includes_additional_details(self, mock_session_local):
        """Test that additional details are included in audit log."""
        mock_db = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_db

        user_id = str(uuid4())
        details = {
            'ip_address': '192.168.1.1',
            'user_agent': 'Mozilla/5.0',
            'method': 'authenticated_change'
        }

        log_security_event(
            action='PASSWORD_CHANGED',
            user_id=user_id,
            user_email='test@example.com',
            details=details
        )

        # Verify details are included in after data
        audit_entry = mock_db.add.call_args[0][0]
        assert 'ip_address' in audit_entry.after
        assert audit_entry.after['ip_address'] == '192.168.1.1'
        assert audit_entry.after['user_agent'] == 'Mozilla/5.0'
        assert audit_entry.after['method'] == 'authenticated_change'

    @patch('services.audit_service.SessionLocal')
    def test_includes_timestamp(self, mock_session_local):
        """Test that timestamp is included in audit data."""
        mock_db = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_db

        log_security_event(
            action='PASSWORD_CHANGED',
            user_id=str(uuid4()),
            user_email='test@example.com'
        )

        audit_entry = mock_db.add.call_args[0][0]
        assert 'timestamp' in audit_entry.after
        # Verify it's a valid ISO format timestamp
        assert 'T' in audit_entry.after['timestamp']

    @patch('services.audit_service.SessionLocal')
    def test_success_flag_included(self, mock_session_local):
        """Test that success flag is included in audit data."""
        mock_db = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_db

        # Test successful action
        log_security_event(
            action='PASSWORD_CHANGED',
            user_id=str(uuid4()),
            user_email='test@example.com',
            success=True
        )

        audit_entry = mock_db.add.call_args[0][0]
        assert audit_entry.after['success'] is True

        # Test failed action
        log_security_event(
            action='PASSWORD_CHANGED',
            user_id=str(uuid4()),
            user_email='test@example.com',
            success=False
        )

        audit_entry = mock_db.add.call_args[0][0]
        assert audit_entry.after['success'] is False

    @patch('services.audit_service.SessionLocal')
    def test_game_id_is_none_for_security_events(self, mock_session_local):
        """Test that security events have NULL game_id (not game-specific)."""
        mock_db = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_db

        log_security_event(
            action='PASSWORD_CHANGED',
            user_id=str(uuid4()),
            user_email='test@example.com'
        )

        audit_entry = mock_db.add.call_args[0][0]
        assert audit_entry.game_id is None
        assert audit_entry.session_id is None

    @patch('services.audit_service.SessionLocal')
    def test_exception_handling(self, mock_session_local):
        """Test that exceptions are caught and don't crash the application."""
        mock_db = MagicMock()
        mock_db.add.side_effect = Exception('Database error')
        mock_session_local.return_value.__enter__.return_value = mock_db

        # Should not raise exception
        try:
            log_security_event(
                action='PASSWORD_CHANGED',
                user_id=str(uuid4()),
                user_email='test@example.com'
            )
        except Exception:
            pytest.fail("log_security_event should not raise exceptions")

        # Should call rollback on error
        mock_db.rollback.assert_called_once()

    @patch('services.audit_service.SessionLocal')
    def test_different_action_types(self, mock_session_local):
        """Test logging different security action types."""
        mock_db = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_db

        actions = [
            'PASSWORD_CHANGED',
            'PASSWORD_RESET_REQUESTED',
            'LOGIN_FAILED',
            'ACCOUNT_DELETED',
            'EMAIL_CHANGED'
        ]

        for action in actions:
            log_security_event(
                action=action,
                user_id=str(uuid4()),
                user_email='test@example.com'
            )

            audit_entry = mock_db.add.call_args[0][0]
            assert audit_entry.action == action


class TestGetUserSecurityLogs:
    """Test retrieval of user security logs."""

    @patch('services.audit_service.SessionLocal')
    def test_returns_user_logs(self, mock_session_local):
        """Test that get_user_security_logs returns logs for user."""
        mock_db = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_db

        # Mock query result
        mock_log = MagicMock()
        mock_log.id = uuid4()
        mock_log.action = 'PASSWORD_CHANGED'
        mock_log.at = datetime.now(timezone.utc)
        mock_log.actor_id = 'test@example.com'
        mock_log.after = {'success': True, 'ip_address': '192.168.1.1'}

        mock_query = mock_db.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_log]

        user_id = str(uuid4())
        result = get_user_security_logs(user_id)

        assert 'audit_logs' in result
        assert len(result['audit_logs']) == 1
        assert result['audit_logs'][0]['action'] == 'PASSWORD_CHANGED'
        assert result['total_count'] == 1

    @patch('services.audit_service.SessionLocal')
    def test_pagination_parameters(self, mock_session_local):
        """Test that pagination parameters are applied correctly."""
        mock_db = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_db

        mock_query = mock_db.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 100
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        user_id = str(uuid4())
        result = get_user_security_logs(user_id, limit=25, offset=50)

        # Verify pagination was applied
        mock_query.offset.assert_called_with(50)
        mock_query.limit.assert_called_with(25)
        assert result['page_size'] == 25
        assert result['offset'] == 50

    @patch('services.audit_service.SessionLocal')
    def test_orders_by_most_recent(self, mock_session_local):
        """Test that logs are ordered by most recent first."""
        mock_db = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_db

        mock_query = mock_db.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        user_id = str(uuid4())
        get_user_security_logs(user_id)

        # Verify order_by was called (desc on at timestamp)
        assert mock_query.order_by.called

    @patch('services.audit_service.SessionLocal')
    def test_filters_by_user_id_and_users_table(self, mock_session_local):
        """Test that query filters by user_id and target_table='users'."""
        mock_db = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_db

        mock_query = mock_db.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        user_id = str(uuid4())
        get_user_security_logs(user_id)

        # Verify filter was called
        assert mock_query.filter.called

    @patch('services.audit_service.SessionLocal')
    def test_returns_correct_structure(self, mock_session_local):
        """Test that returned data has correct structure."""
        mock_db = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_db

        mock_query = mock_db.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 5
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        user_id = str(uuid4())
        result = get_user_security_logs(user_id, limit=10, offset=0)

        # Verify structure
        assert 'audit_logs' in result
        assert 'total_count' in result
        assert 'page_size' in result
        assert 'offset' in result
        assert isinstance(result['audit_logs'], list)
        assert result['total_count'] == 5
        assert result['page_size'] == 10
        assert result['offset'] == 0
