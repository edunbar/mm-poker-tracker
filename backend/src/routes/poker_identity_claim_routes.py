"""
Poker Identity Claim API routes.

This module provides endpoints for users to claim and manage their poker player
identities, linking their user account to player records from imported games.
"""

from flask import Blueprint, request, jsonify, g

from db.database import SessionLocal
from db.models import Game
from infrastructure.persistence.sqlalchemy.poker_identity_claim_repository import (
    SQLAlchemyPokerIdentityClaimRepository
)
from infrastructure.persistence.sqlalchemy.player_repository import (
    SQLAlchemyPlayerRepository
)
from domain.identity import PokerIdentityClaimService
from domain.identity.value_objects import UserId
from domain.identity.exceptions import (
    PlayerNotFoundError,
    PlayerAlreadyClaimedError,
    ClaimNotFoundError,
    UnauthorizedClaimError
)
from domain.poker.value_objects import PlayerId, GameId
from middleware.auth_middleware import require_auth

# Create blueprint
poker_identity_bp = Blueprint('poker_identity_claims', __name__)


# ============================================================================
# Helper Functions (Dependency Injection)
# ============================================================================

def get_claim_service(db_session) -> PokerIdentityClaimService:
    """
    Create PokerIdentityClaimService with all dependencies.

    This helper prevents code duplication across routes and centralizes
    dependency injection.

    Args:
        db_session: SQLAlchemy database session

    Returns:
        Configured PokerIdentityClaimService instance
    """
    claim_repo = SQLAlchemyPokerIdentityClaimRepository(db_session)
    player_repo = SQLAlchemyPlayerRepository(db_session)
    return PokerIdentityClaimService(claim_repo, player_repo)


def get_existing_claim_for_game(db_session, user_id: str, game_id: str):
    """
    Check if user has claimed a player identity in this game.

    This helper is used during live game joining to determine if a user
    should be auto-linked to an existing claimed player or if they need
    to go through the claiming flow.

    Args:
        db_session: SQLAlchemy database session
        user_id: User UUID string
        game_id: Game UUID string

    Returns:
        PokerIdentityClaim if user has claimed a player in this game, None otherwise

    Example:
        >>> claim = get_existing_claim_for_game(db, user.id, game.id)
        >>> if claim:
        >>>     # Auto-link to claim.player_id
        >>> else:
        >>>     # Show claiming screen
    """
    from db.models import PokerIdentityClaim as PokerIdentityClaimModel
    from db.models import Player as PlayerModel
    from db.models import GamePlayer as GamePlayerModel

    claim = db_session.query(PokerIdentityClaimModel).join(
        PlayerModel, PokerIdentityClaimModel.player_id == PlayerModel.id
    ).join(
        GamePlayerModel, PlayerModel.id == GamePlayerModel.player_id
    ).filter(
        PokerIdentityClaimModel.user_id == user_id,
        GamePlayerModel.game_id == game_id
    ).first()

    return claim


# ============================================================================
# API Routes
# ============================================================================

@poker_identity_bp.route('/me', methods=['GET'])
@require_auth
def get_my_claims():
    """
    Get all claimed player identities for the current authenticated user.

    Headers:
        Authorization: Bearer <jwt_token>

    Returns:
        200: {
            "claims": [
                {
                    "claim_id": "uuid",
                    "player_id": "uuid",
                    "player_name": "Player Name",
                    "claimed_at": "2025-01-15T10:30:00Z",
                    "verification_method": "manual",
                    "games": [
                        {
                            "game_id": "uuid",
                            "public_code": "ABC123",
                            "game_title": "My Poker Game"
                        }
                    ]
                }
            ]
        }

        401: { "error": "authentication error message" }
        500: { "error": "server error message" }

    Note:
        Requires valid JWT token in Authorization header.
        User info is injected by @require_auth decorator via g.current_user_id
    """
    db = SessionLocal()
    try:
        # Get user ID from JWT payload (injected by @require_auth)
        user_id = UserId(g.current_user_id)

        # Initialize service
        service = get_claim_service(db)

        # Get user claims with details
        claims = service.get_user_claims(user_id)

        return jsonify({'claims': claims}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch claims: {str(e)}'}), 500

    finally:
        db.close()


@poker_identity_bp.route('/games/<public_code>/claimable', methods=['GET'])
@require_auth
def get_claimable_players(public_code):
    """
    Get all unclaimed players in a specific game.

    Headers:
        Authorization: Bearer <jwt_token>

    Path Parameters:
        public_code: Public code of the game (e.g., "C4QRO")

    Returns:
        200: {
            "claimable_players": [
                {
                    "player_id": "uuid",
                    "player_name": "Player Name",
                    "session_count": 5
                }
            ]
        }

        404: { "error": "Game not found" }
        401: { "error": "authentication error message" }
        500: { "error": "server error message" }

    Note:
        Returns empty list if no claimable players exist.
        Players already claimed by any user are excluded.
    """
    db = SessionLocal()
    try:
        # Look up game by public code (following existing pattern)
        game = db.query(Game).filter(Game.public_code == public_code.upper()).first()
        if not game:
            return jsonify({'error': 'Game not found'}), 404

        # Convert to GameId value object
        game_id_vo = GameId(str(game.id))

        # Initialize service
        service = get_claim_service(db)

        # Get claimable players
        claimable_players = service.get_claimable_players_in_game(game_id_vo)

        return jsonify({'claimable_players': claimable_players}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch claimable players: {str(e)}'}), 500

    finally:
        db.close()


@poker_identity_bp.route('/claim', methods=['POST'])
@require_auth
def claim_player():
    """
    Claim a poker player identity.

    Headers:
        Authorization: Bearer <jwt_token>

    Request Body:
        {
            "player_id": "uuid-string",  // required
            "verification_method": "manual"  // optional, defaults to 'manual'
        }

    Returns:
        201: {
            "message": "Player identity claimed successfully",
            "claim": {
                "id": "uuid",
                "user_id": "uuid",
                "player_id": "uuid",
                "claimed_at": "2025-01-15T10:30:00Z",
                "verification_method": "manual"
            }
        }

        400: { "error": "validation or business logic error message" }
            - Missing player_id
            - Invalid player_id format
            - Player already claimed
        401: { "error": "authentication error message" }
        404: { "error": "Player not found" }
        500: { "error": "server error message" }

    Note:
        Validation includes:
        - Player must exist
        - Player cannot already be claimed by any user
        - If already claimed by requesting user, returns specific error message
    """
    db = SessionLocal()
    try:
        # Parse request
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        # Validate required fields
        if 'player_id' not in data:
            return jsonify({'error': 'Missing required field: player_id'}), 400

        player_id_str = data['player_id']
        verification_method = data.get('verification_method', 'manual')

        # Validate and convert player_id to value object
        try:
            player_id = PlayerId(player_id_str)
        except ValueError as e:
            return jsonify({'error': f'Invalid player_id: {str(e)}'}), 400

        # Get user ID from JWT payload (injected by @require_auth)
        user_id = UserId(g.current_user_id)

        # Initialize service
        service = get_claim_service(db)

        # Claim the player
        claim = service.claim_player(user_id, player_id, verification_method)

        # Commit the transaction
        db.commit()

        return jsonify({
            'message': 'Player identity claimed successfully',
            'claim': claim.to_dict()
        }), 201

    except PlayerNotFoundError as e:
        return jsonify({'error': e.message}), 404

    except PlayerAlreadyClaimedError as e:
        return jsonify({'error': e.message}), 400

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to claim player: {str(e)}'}), 500

    finally:
        db.close()


@poker_identity_bp.route('/<claim_id>', methods=['DELETE'])
@require_auth
def unclaim_player(claim_id):
    """
    Unclaim a poker player identity.

    Headers:
        Authorization: Bearer <jwt_token>

    Path Parameters:
        claim_id: UUID string of the claim to remove

    Returns:
        200: { "message": "Player identity unclaimed successfully" }

        401: { "error": "authentication error message" }
        403: { "error": "Not authorized to delete this claim" }
        404: { "error": "Claim not found" }
        500: { "error": "server error message" }

    Note:
        Users can only unclaim their own claims.
        Attempting to unclaim another user's claim returns 403.
    """
    db = SessionLocal()
    try:
        # Get user ID from JWT payload (injected by @require_auth)
        user_id = UserId(g.current_user_id)

        # Initialize service
        service = get_claim_service(db)

        # Unclaim the player
        success = service.unclaim_player(user_id, claim_id)

        if success:
            # Commit the transaction
            db.commit()
            return jsonify({'message': 'Player identity unclaimed successfully'}), 200
        else:
            return jsonify({'error': 'Failed to delete claim'}), 500

    except ClaimNotFoundError as e:
        return jsonify({'error': e.message}), 404

    except UnauthorizedClaimError as e:
        return jsonify({'error': e.message}), 403

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to unclaim player: {str(e)}'}), 500

    finally:
        db.close()


@poker_identity_bp.route('/players/<player_id>/preview', methods=['GET'])
@require_auth
def preview_player(player_id):
    """
    Get preview data for a player before claiming.

    Headers:
        Authorization: Bearer <jwt_token>

    Path Parameters:
        player_id: UUID string of the player

    Returns:
        200: {
            "player_id": "uuid",
            "player_name": "Player Name",
            "session_count": 5
        }

        400: { "error": "Invalid player ID format" }
        401: { "error": "authentication error message" }
        404: { "error": "Player not found" }
        500: { "error": "server error message" }

    Note:
        Provides basic player information to help users identify
        which player identity they want to claim.
    """
    db = SessionLocal()
    try:
        # Validate and convert player_id to value object
        try:
            player_id_vo = PlayerId(player_id)
        except ValueError as e:
            return jsonify({'error': f'Invalid player_id: {str(e)}'}), 400

        # Get player from repository
        player_repo = SQLAlchemyPlayerRepository(db)
        player = player_repo.get_by_id(player_id_vo)

        if not player:
            return jsonify({'error': 'Player not found'}), 404

        # Build preview response
        preview_data = {
            'player_id': str(player.player_id),
            'player_name': str(player.display_name),
            'session_count': len(player.sessions)
        }

        return jsonify(preview_data), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch player preview: {str(e)}'}), 500

    finally:
        db.close()
