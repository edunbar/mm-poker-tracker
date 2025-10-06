"""
Unit/integration tests for authorization logic.

Tests the check_game_authorization() helper function directly
to ensure proper authorization checks for JWT and admin code auth.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from middleware.auth_middleware import check_game_authorization
from db.models import Game


class TestAuthorizationLogic:
    """Test suite for authorization helper function."""

    def test_authorization_jwt_game_owner(self):
        """JWT auth with game ownership should pass."""
        # Create game owned by user
        user_id = str(uuid4())
        game = Game(
            public_code='TEST123',
            admin_code='admin-secret',
            owner_user_id=user_id,
            title='Test Game'
        )

        # Check authorization with correct user_id
        authorized, error_msg = check_game_authorization(
            game=game,
            auth_method='jwt',
            user_id=user_id,
            admin_code=None
        )

        assert authorized is True
        assert error_msg == ""

    def test_authorization_jwt_not_owner(self):
        """JWT auth without ownership should fail."""
        # Create game owned by one user
        owner_id = str(uuid4())
        other_user_id = str(uuid4())

        game = Game(
            public_code='TEST456',
            admin_code='admin-secret',
            owner_user_id=owner_id,
            title='Test Game'
        )

        # Check authorization with different user_id
        authorized, error_msg = check_game_authorization(
            game=game,
            auth_method='jwt',
            user_id=other_user_id,
            admin_code=None
        )

        assert authorized is False
        assert "not authorized" in error_msg.lower() or "do not own" in error_msg.lower()

    def test_authorization_admin_code_unclaimed_game(self):
        """Admin code on unclaimed game should pass."""
        # Create unclaimed game (owner_user_id is None)
        game = Game(
            public_code='TEST789',
            admin_code='admin-secret-code',
            owner_user_id=None,  # Unclaimed
            title='Unclaimed Game'
        )

        # Check authorization with admin code
        authorized, error_msg = check_game_authorization(
            game=game,
            auth_method='admin_code',
            user_id=None,
            admin_code='admin-secret-code'
        )

        assert authorized is True
        assert error_msg == ""

    def test_authorization_admin_code_within_grace_period(self):
        """Admin code within 90 days should pass."""
        # Create claimed game with expiration in future
        game = Game(
            public_code='TESTGRACE',
            admin_code='admin-code-123',
            owner_user_id=str(uuid4()),  # Claimed
            admin_code_expires_at=datetime.now(timezone.utc) + timedelta(days=30),  # Still valid
            title='Claimed Game'
        )

        # Check authorization with admin code
        authorized, error_msg = check_game_authorization(
            game=game,
            auth_method='admin_code',
            user_id=None,
            admin_code='admin-code-123'
        )

        assert authorized is True
        assert error_msg == ""

    def test_authorization_admin_code_expired(self):
        """Admin code after 90 days should fail."""
        # Create claimed game with expired admin code
        game = Game(
            public_code='TESTEXPIRED',
            admin_code='admin-expired-code',
            owner_user_id=str(uuid4()),  # Claimed
            admin_code_expires_at=datetime.now(timezone.utc) - timedelta(days=1),  # Expired
            title='Expired Admin Code Game'
        )

        # Check authorization with admin code
        authorized, error_msg = check_game_authorization(
            game=game,
            auth_method='admin_code',
            user_id=None,
            admin_code='admin-expired-code'
        )

        assert authorized is False
        assert "expired" in error_msg.lower()
