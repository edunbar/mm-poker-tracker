"""
Integration tests for Player Identity Claims feature.

This module tests the complete player identity claiming workflow including:
- Claiming and unclaiming players
- Validation and authorization rules
- Database cascade behavior
- Query operations
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone

from db.database import SessionLocal
from db.models import User, Game, Player, GamePlayer, PokerIdentityClaim
from domain.identity import PokerIdentityClaimService
from domain.identity.value_objects import UserId
from domain.identity.exceptions import (
    PlayerNotFoundError,
    PlayerAlreadyClaimedError,
    ClaimNotFoundError,
    UnauthorizedClaimError
)
from domain.poker.value_objects import PlayerId, GameId
from infrastructure.persistence.sqlalchemy.poker_identity_claim_repository import (
    SQLAlchemyPokerIdentityClaimRepository
)
from infrastructure.persistence.sqlalchemy.player_repository import (
    SQLAlchemyPlayerRepository
)
from infrastructure.security.bcrypt_password_hasher import BcryptPasswordHasher


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def setup_test_data():
    """
    Create test data for player identity claims tests.

    Creates:
    - 2 test users (user1, user2)
    - 1 test game with 3 players (player1, player2, player3)
    - 1 initial claim (user1 → player1)

    Returns:
        dict with all test entity IDs
    """
    db = SessionLocal()
    password_hasher = BcryptPasswordHasher()

    try:
        # Create test users
        user1 = User(
            email='claimtest1@example.com',
            password_hash=password_hasher.hash('TestPass123!'),
            display_name='Claim Test User 1',
            email_verified=True
        )
        user2 = User(
            email='claimtest2@example.com',
            password_hash=password_hasher.hash('TestPass123!'),
            display_name='Claim Test User 2',
            email_verified=True
        )
        db.add(user1)
        db.add(user2)
        db.flush()

        # Create test game
        game = Game(
            public_code='CLMTST',
            admin_code='test-admin-code-claims',
            title='Player Claim Test Game',
            meta={}
        )
        db.add(game)
        db.flush()

        # Create test players
        player1 = Player(display_name='ClaimTestPlayer1')
        player2 = Player(display_name='ClaimTestPlayer2')
        player3 = Player(display_name='ClaimTestPlayer3')
        db.add_all([player1, player2, player3])
        db.flush()

        # Link players to game
        for player in [player1, player2, player3]:
            game_player = GamePlayer(
                game_id=game.id,
                player_id=player.id
            )
            db.add(game_player)
        db.flush()

        # Create initial claim (user1 → player1)
        claim1 = PokerIdentityClaim(
            user_id=user1.id,
            player_id=player1.id,
            verification_method='manual',
            claimed_at=datetime.now(timezone.utc)
        )
        db.add(claim1)
        db.commit()

        # Return test data IDs
        yield {
            'user1_id': str(user1.id),
            'user2_id': str(user2.id),
            'game_id': str(game.id),
            'player1_id': str(player1.id),  # claimed by user1
            'player2_id': str(player2.id),  # unclaimed
            'player3_id': str(player3.id),  # unclaimed
            'claim1_id': str(claim1.id)
        }

    finally:
        # Cleanup - delete test data
        try:
            # Delete using email since variables might not be initialized if error occurred
            db.query(PokerIdentityClaim).filter(
                PokerIdentityClaim.user_id.in_(
                    db.query(User.id).filter(
                        User.email.in_(['claimtest1@example.com', 'claimtest2@example.com'])
                    )
                )
            ).delete(synchronize_session=False)

            # Delete game and related data
            test_game = db.query(Game).filter(Game.public_code == 'CLMTST').first()
            if test_game:
                db.query(GamePlayer).filter(GamePlayer.game_id == test_game.id).delete(synchronize_session=False)
                db.query(Player).filter(
                    Player.id.in_(
                        db.query(GamePlayer.player_id).filter(GamePlayer.game_id == test_game.id)
                    )
                ).delete(synchronize_session=False)
                db.query(Game).filter(Game.id == test_game.id).delete(synchronize_session=False)

            # Delete test users
            db.query(User).filter(
                User.email.in_(['claimtest1@example.com', 'claimtest2@example.com'])
            ).delete(synchronize_session=False)

            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


@pytest.fixture
def claim_service():
    """Create PokerIdentityClaimService with fresh database session."""
    db = SessionLocal()
    claim_repo = SQLAlchemyPokerIdentityClaimRepository(db)
    player_repo = SQLAlchemyPlayerRepository(db)
    service = PokerIdentityClaimService(claim_repo, player_repo)

    yield service

    db.close()


# ============================================================================
# Test Class
# ============================================================================

class TestPlayerIdentityClaims:
    """Integration tests for Player Identity Claims domain service."""

    def test_claim_player_success(self, setup_test_data, claim_service):
        """User successfully claims an unclaimed player."""
        user2_id = UserId(setup_test_data['user2_id'])
        player2_id = PlayerId(setup_test_data['player2_id'])

        # Claim player2 as user2
        claim = claim_service.claim_player(
            user_id=user2_id,
            player_id=player2_id,
            verification_method='manual'
        )

        # Verify claim was created
        assert claim is not None
        assert str(claim.user_id) == setup_test_data['user2_id']
        assert str(claim.player_id) == setup_test_data['player2_id']
        assert claim.verification_method == 'manual'
        assert claim.claimed_at is not None

        # Verify player is now claimed
        is_claimed = claim_service.is_player_claimed(player2_id)
        assert is_claimed is True

    def test_claim_player_already_claimed_by_self(self, setup_test_data, claim_service):
        """User tries to claim a player they already claimed."""
        user1_id = UserId(setup_test_data['user1_id'])
        player1_id = PlayerId(setup_test_data['player1_id'])  # already claimed by user1

        # Try to claim player1 again as user1
        with pytest.raises(PlayerAlreadyClaimedError) as exc_info:
            claim_service.claim_player(
                user_id=user1_id,
                player_id=player1_id,
                verification_method='manual'
            )

        assert 'You have already claimed player' in str(exc_info.value)

    def test_claim_player_already_claimed_by_other(self, setup_test_data, claim_service):
        """User tries to claim a player already claimed by another user."""
        user2_id = UserId(setup_test_data['user2_id'])
        player1_id = PlayerId(setup_test_data['player1_id'])  # already claimed by user1

        # Try to claim player1 as user2
        with pytest.raises(PlayerAlreadyClaimedError) as exc_info:
            claim_service.claim_player(
                user_id=user2_id,
                player_id=player1_id,
                verification_method='manual'
            )

        assert 'already been claimed' in str(exc_info.value)

    def test_claim_player_not_found(self, setup_test_data, claim_service):
        """User tries to claim a non-existent player."""
        user1_id = UserId(setup_test_data['user1_id'])
        fake_player_id = PlayerId(str(uuid4()))

        # Try to claim non-existent player
        with pytest.raises(PlayerNotFoundError) as exc_info:
            claim_service.claim_player(
                user_id=user1_id,
                player_id=fake_player_id,
                verification_method='manual'
            )

        assert 'was not found' in str(exc_info.value)

    def test_unclaim_player_success(self, setup_test_data, claim_service):
        """User successfully unclaims their own player."""
        user1_id = UserId(setup_test_data['user1_id'])
        claim1_id = setup_test_data['claim1_id']
        player1_id = PlayerId(setup_test_data['player1_id'])

        # Unclaim player1
        result = claim_service.unclaim_player(user1_id, claim1_id)
        assert result is True

        # Verify player is no longer claimed
        is_claimed = claim_service.is_player_claimed(player1_id)
        assert is_claimed is False

    def test_unclaim_player_not_owned(self, setup_test_data, claim_service):
        """User tries to unclaim another user's claim."""
        user2_id = UserId(setup_test_data['user2_id'])
        claim1_id = setup_test_data['claim1_id']  # owned by user1

        # Try to unclaim user1's claim as user2
        with pytest.raises(UnauthorizedClaimError) as exc_info:
            claim_service.unclaim_player(user2_id, claim1_id)

        assert 'not authorized to modify claim' in str(exc_info.value)

    def test_unclaim_nonexistent_claim(self, setup_test_data, claim_service):
        """User tries to unclaim a non-existent claim."""
        user1_id = UserId(setup_test_data['user1_id'])
        fake_claim_id = str(uuid4())

        # Try to unclaim non-existent claim
        with pytest.raises(ClaimNotFoundError) as exc_info:
            claim_service.unclaim_player(user1_id, fake_claim_id)

        assert 'was not found' in str(exc_info.value)

    def test_is_player_claimed(self, setup_test_data, claim_service):
        """Check if player is claimed returns correct status."""
        player1_id = PlayerId(setup_test_data['player1_id'])  # claimed
        player2_id = PlayerId(setup_test_data['player2_id'])  # unclaimed

        # Check claimed player
        assert claim_service.is_player_claimed(player1_id) is True

        # Check unclaimed player
        assert claim_service.is_player_claimed(player2_id) is False

    def test_get_user_claims_with_details(self, setup_test_data, claim_service):
        """Get all claims for a user with game details."""
        user1_id = UserId(setup_test_data['user1_id'])

        # Get claims for user1
        claims = claim_service.get_user_claims(user1_id)

        # Verify structure
        assert len(claims) == 1
        claim = claims[0]

        # Verify claim data
        assert claim['claim_id'] == setup_test_data['claim1_id']
        assert claim['player_id'] == setup_test_data['player1_id']
        assert claim['player_name'] == 'ClaimTestPlayer1'
        assert claim['verification_method'] == 'manual'
        assert 'claimed_at' in claim

        # Verify games array
        assert 'games' in claim
        assert len(claim['games']) > 0
        game = claim['games'][0]
        assert game['game_id'] == setup_test_data['game_id']
        assert game['public_code'] == 'CLMTST'
        assert game['game_title'] == 'Player Claim Test Game'

    def test_get_claimable_players_in_game(self, setup_test_data, claim_service):
        """Get all unclaimed players in a specific game."""
        game_id = GameId(setup_test_data['game_id'])

        # Get claimable players
        claimable = claim_service.get_claimable_players_in_game(game_id)

        # Should have 2 claimable players (player2, player3)
        # player1 is claimed by user1
        assert len(claimable) == 2

        # Extract player IDs
        claimable_ids = [p['player_id'] for p in claimable]
        assert setup_test_data['player2_id'] in claimable_ids
        assert setup_test_data['player3_id'] in claimable_ids
        assert setup_test_data['player1_id'] not in claimable_ids  # already claimed

        # Verify structure of claimable player data
        player = claimable[0]
        assert 'player_id' in player
        assert 'player_name' in player
        assert 'session_count' in player

    def test_get_claim_for_player(self, setup_test_data, claim_service):
        """Get claim for a specific player."""
        player1_id = PlayerId(setup_test_data['player1_id'])  # claimed
        player2_id = PlayerId(setup_test_data['player2_id'])  # unclaimed

        # Get claim for claimed player
        claim = claim_service.get_claim_for_player(player1_id)
        assert claim is not None
        assert str(claim.player_id) == setup_test_data['player1_id']
        assert str(claim.user_id) == setup_test_data['user1_id']

        # Get claim for unclaimed player - should raise exception
        with pytest.raises(ClaimNotFoundError) as exc_info:
            claim_service.get_claim_for_player(player2_id)

        assert 'is not claimed' in str(exc_info.value)

    def test_cascade_delete_user(self, setup_test_data):
        """Deleting a user should cascade delete their claims."""
        db = SessionLocal()

        try:
            user1_id = setup_test_data['user1_id']
            claim1_id = setup_test_data['claim1_id']

            # Verify claim exists before deletion
            claim_before = db.query(PokerIdentityClaim).filter(
                PokerIdentityClaim.id == claim1_id
            ).first()
            assert claim_before is not None

            # Delete user1
            user = db.query(User).filter(User.id == user1_id).first()
            db.delete(user)
            db.commit()

            # Verify claim was cascade deleted
            claim_after = db.query(PokerIdentityClaim).filter(
                PokerIdentityClaim.id == claim1_id
            ).first()
            assert claim_after is None

        finally:
            db.close()


# ============================================================================
# API Route Integration Tests
# ============================================================================

class TestPlayerIdentityClaimRoutes:
    """Integration tests for Player Identity Claim API routes."""

    def test_get_my_claims_authenticated(self, setup_test_data):
        """GET /api/identity/me returns user's claims when authenticated."""
        # Note: This test requires a test_client fixture with authentication
        # Placeholder for future API route testing
        pass

    def test_get_claimable_players_by_public_code(self, setup_test_data):
        """GET /api/identity/games/<public_code>/claimable returns unclaimed players."""
        # Note: This test requires a test_client fixture with authentication
        # Placeholder for future API route testing
        pass

    def test_claim_player_via_api(self, setup_test_data):
        """POST /api/identity/claim creates a new claim."""
        # Note: This test requires a test_client fixture with authentication
        # Placeholder for future API route testing
        pass

    def test_unclaim_player_via_api(self, setup_test_data):
        """DELETE /api/identity/<claim_id> removes a claim."""
        # Note: This test requires a test_client fixture with authentication
        # Placeholder for future API route testing
        pass
