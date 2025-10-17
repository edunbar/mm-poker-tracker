"""
Live Game API routes.

This module provides REST endpoints for managing real-time live poker game
sessions, including game creation, participant management, transaction handling,
and game closure with reconciliation.
"""

from decimal import Decimal, InvalidOperation
from flask import Blueprint, request, jsonify, g

from db.database import SessionLocal
from db.models import Game as GameModel
from middleware.clerk_auth import clerk_required, get_current_user

from domain.identity.value_objects import UserId
from domain.poker.value_objects import GameId
from domain.live_game import (
    LiveGameService,
    LiveGamePermissionService,
    LiveGameRepository,
    ParticipantRepository,
    TransactionRepository,
    LiveGameId,
    TransactionId,
    LiveGameNotFoundError,
    LiveGameAlreadyClosedError,
    ActiveLiveGameExistsError,
    InvalidJoinCodeError,
    ParticipantAlreadyJoinedError,
    ParticipantNotFoundError,
    InvalidBuyInAmountError,
    InvalidCashOutAmountError,
    TransactionNotFoundError,
    TransactionNotPendingError,
    UnauthorizedApprovalError,
    GameNotBalancedError,
    PlayersStillActiveError
)
from infrastructure.persistence.sqlalchemy import (
    SQLAlchemyLiveGameRepository,
    SQLAlchemyParticipantRepository,
    SQLAlchemyTransactionRepository
)

# Import SSE broadcasting
from routes.live_game_sse import broadcast_event

# Create blueprint
live_game_bp = Blueprint('live_game', __name__)


# ============================================================================
# Helper Functions (Dependency Injection)
# ============================================================================

def get_live_game_service(db_session) -> LiveGameService:
    """
    Create LiveGameService with all dependencies.

    Args:
        db_session: SQLAlchemy database session

    Returns:
        Configured LiveGameService instance
    """
    live_game_repo = SQLAlchemyLiveGameRepository(db_session)
    participant_repo = SQLAlchemyParticipantRepository(db_session)
    transaction_repo = SQLAlchemyTransactionRepository(db_session)

    return LiveGameService(
        live_game_repo=live_game_repo,
        participant_repo=participant_repo,
        transaction_repo=transaction_repo
    )


def get_permission_service(db_session) -> LiveGamePermissionService:
    """
    Create LiveGamePermissionService with dependencies.

    Args:
        db_session: SQLAlchemy database session

    Returns:
        Configured LiveGamePermissionService instance
    """
    live_game_repo = SQLAlchemyLiveGameRepository(db_session)
    return LiveGamePermissionService(live_game_repo=live_game_repo)


def check_admin_session(db_session, user_id: UserId, game_id: str) -> bool:
    """
    Check if user owns the parent game (has admin access).

    Args:
        db_session: SQLAlchemy database session
        user_id: User to check
        game_id: Game identifier (UUID string)

    Returns:
        True if user owns the game, False otherwise
    """
    game = db_session.query(GameModel).filter(GameModel.id == game_id).first()

    if not game:
        return False

    # User has admin access if they own the game
    return game.owner_user_id is not None and str(game.owner_user_id) == str(user_id)


# ============================================================================
# Game Management - Parent Game Pattern
# ============================================================================

@live_game_bp.route('/games/<game_id>/live-games', methods=['POST'])
@clerk_required
def create_live_game(game_id):
    """
    Create a new live game session for a parent game.

    Path Parameters:
        game_id: Parent game UUID

    Request Body:
        {
            "small_blind": 0.50,  // optional
            "big_blind": 1.00,    // optional
            "min_buy_in": 20.00,  // required
            "max_buy_in": 100.00  // optional
        }

    Returns:
        201: {
            "live_game_id": "uuid",
            "game_id": "uuid",
            "join_code": "A3B7",
            "status": "active",
            "created_by_user_id": "uuid",
            "small_blind": 0.50,
            "big_blind": 1.00,
            "min_buy_in": 20.00,
            "max_buy_in": 100.00,
            "started_at": "2025-10-10T12:00:00Z"
        }

        400: { "error": "validation error message" }
        401: { "error": "authentication error" }
        404: { "error": "Game not found" }
        409: { "error": "Active live game already exists with code: XXXX" }
        500: { "error": "server error message" }
    """
    db = SessionLocal()
    try:
        # Verify game exists
        game = db.query(GameModel).filter(GameModel.id == game_id).first()
        if not game:
            return jsonify({'error': 'Game not found'}), 404

        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        # Validate required fields
        if 'min_buy_in' not in data:
            return jsonify({'error': 'Missing required field: min_buy_in'}), 400

        try:
            min_buy_in = Decimal(str(data['min_buy_in']))
        except (InvalidOperation, ValueError):
            return jsonify({'error': 'Invalid min_buy_in: must be a valid number'}), 400

        # Optional fields
        small_blind = None
        big_blind = None
        max_buy_in = None

        if 'small_blind' in data:
            try:
                small_blind = Decimal(str(data['small_blind']))
            except (InvalidOperation, ValueError):
                return jsonify({'error': 'Invalid small_blind: must be a valid number'}), 400

        if 'big_blind' in data:
            try:
                big_blind = Decimal(str(data['big_blind']))
            except (InvalidOperation, ValueError):
                return jsonify({'error': 'Invalid big_blind: must be a valid number'}), 400

        if 'max_buy_in' in data:
            try:
                max_buy_in = Decimal(str(data['max_buy_in']))
            except (InvalidOperation, ValueError):
                return jsonify({'error': 'Invalid max_buy_in: must be a valid number'}), 400

        # Create service and live game
        service = get_live_game_service(db)
        current_user_id = UserId(str(get_current_user().id))

        live_game = service.create_live_game(
            game_id=GameId(game_id),
            created_by_user_id=current_user_id,
            small_blind=small_blind,
            big_blind=big_blind,
            min_buy_in=min_buy_in,
            max_buy_in=max_buy_in
        )

        db.commit()

        return jsonify({
            'live_game_id': str(live_game.id),
            'game_id': str(live_game.game_id),
            'join_code': live_game.join_code.value,
            'status': live_game.status,
            'created_by_user_id': str(live_game.created_by_user_id),
            'small_blind': float(live_game.small_blind) if live_game.small_blind else None,
            'big_blind': float(live_game.big_blind) if live_game.big_blind else None,
            'min_buy_in': float(live_game.min_buy_in),
            'max_buy_in': float(live_game.max_buy_in) if live_game.max_buy_in else None,
            'started_at': live_game.started_at.isoformat()
        }), 201

    except ActiveLiveGameExistsError as e:
        return jsonify({'error': str(e), 'existing_join_code': e.existing_join_code}), 409

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to create live game: {str(e)}'}), 500

    finally:
        db.close()


@live_game_bp.route('/games/<game_id>/live-games/active', methods=['GET'])
def get_active_live_game(game_id):
    """
    Get active live game for a parent game.

    Path Parameters:
        game_id: Parent game UUID

    Returns:
        200: {
            "live_game_id": "uuid",
            "join_code": "A3B7",
            "status": "active",
            "started_at": "2025-10-10T12:00:00Z",
            "participant_count": 5
        }

        404: { "error": "No active live game found" }
        500: { "error": "server error message" }
    """
    db = SessionLocal()
    try:
        service = get_live_game_service(db)
        live_game = service.get_active_live_game(GameId(game_id))

        if not live_game:
            return jsonify({'error': 'No active live game found'}), 404

        # Get participant count
        participants = service.get_participants(live_game.id)

        return jsonify({
            'live_game_id': str(live_game.id),
            'join_code': live_game.join_code.value,
            'status': live_game.status,
            'started_at': live_game.started_at.isoformat(),
            'participant_count': len(participants)
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch active live game: {str(e)}'}), 500

    finally:
        db.close()


@live_game_bp.route('/games/public/<public_code>/live-games/active', methods=['GET'])
def get_active_live_game_by_public_code(public_code):
    """
    Get active live game for a parent game using public code.

    Path Parameters:
        public_code: Parent game public code (e.g., "C4QROK")

    Returns:
        200: {
            "live_game_id": "uuid",
            "join_code": "A3B7",
            "status": "active",
            "started_at": "2025-10-10T12:00:00Z",
            "participant_count": 5
        }

        404: { "error": "No active live game found" | "Game not found" }
        500: { "error": "server error message" }
    """
    db = SessionLocal()
    try:
        # Lookup game by public code to get game_id (UUID)
        game = db.query(GameModel).filter(GameModel.public_code == public_code).first()
        if not game:
            return jsonify({'error': 'Game not found'}), 404

        # Get active live game using game_id
        service = get_live_game_service(db)
        live_game = service.get_active_live_game(GameId(str(game.id)))

        if not live_game:
            return jsonify({'error': 'No active live game found'}), 404

        # Get participant count
        participants = service.get_participants(live_game.id)

        return jsonify({
            'live_game_id': str(live_game.id),
            'game_id': str(live_game.game_id),
            'join_code': live_game.join_code.value,
            'status': live_game.status,
            'started_at': live_game.started_at.isoformat(),
            'participant_count': len(participants)
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch active live game: {str(e)}'}), 500

    finally:
        db.close()


# ============================================================================
# Game Management - Join Code Pattern
# ============================================================================

@live_game_bp.route('/live-games/join', methods=['POST'])
@clerk_required
def join_live_game():
    """
    Join a live game using a join code with player identity claiming.

    NEW BEHAVIOR (Player Identity Claiming):
    1. Check if user already joined → return already_joined
    2. Check for existing player claim in parent game:
       - If claim exists → auto-link to claimed player
       - If no claim → return needs_claim with available players

    Request Body:
        {
            "join_code": "A3B7",
            "display_name": "John Doe"
        }

    Returns:
        200 (already joined): {
            "already_joined": true,
            "participant_id": "uuid",
            "display_name": "John Doe",
            "player": {
                "id": "uuid",
                "name": "Player Name"
            } // optional, if player_id is linked
        }

        200 (needs claim): {
            "needs_claim": true,
            "available_players": [
                {
                    "player_id": "uuid",
                    "player_name": "Player Name",
                    "session_count": 5
                }
            ]
        }

        201 (auto-linked): {
            "participant_id": "uuid",
            "live_game_id": "uuid",
            "user_id": "uuid",
            "display_name": "John Doe",
            "player_id": "uuid",
            "joined_at": "2025-10-10T12:05:00Z",
            "auto_linked": true,
            "player": {
                "id": "uuid",
                "name": "Player Name"
            }
        }

        400: { "error": "validation error message" }
        401: { "error": "authentication error" }
        404: { "error": "Invalid or expired join code: XXXX" }
        410: { "error": "Cannot modify a closed live game" }
        500: { "error": "server error message" }
    """
    db = SessionLocal()
    try:
        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        # Validate required fields
        if 'join_code' not in data:
            return jsonify({'error': 'Missing required field: join_code'}), 400
        if 'display_name' not in data:
            return jsonify({'error': 'Missing required field: display_name'}), 400

        join_code_str = data['join_code'].strip().upper()
        display_name = data['display_name'].strip()

        if not display_name:
            return jsonify({'error': 'Display name cannot be empty'}), 400

        # Get live game by join code
        service = get_live_game_service(db)
        live_game = service.get_live_game_by_join_code(join_code_str)
        current_user_id = UserId(str(get_current_user().id))

        # ===== STEP 1: Check if user already joined this live game =====
        from db.models import LiveGameParticipant as LiveGameParticipantModel
        from db.models import Player as PlayerModel

        existing_participant = db.query(LiveGameParticipantModel).filter(
            LiveGameParticipantModel.user_id == str(current_user_id),
            LiveGameParticipantModel.live_game_id == str(live_game.id)
        ).first()

        if existing_participant:
            # Get player info if linked
            player_info = None
            if existing_participant.player_id:
                player = db.query(PlayerModel).filter(PlayerModel.id == existing_participant.player_id).first()
                if player:
                    player_info = {'id': str(player.id), 'name': player.display_name}

            return jsonify({
                'already_joined': True,
                'participant_id': str(existing_participant.id),
                'display_name': existing_participant.display_name,
                'player': player_info
            }), 200

        # ===== STEP 2: Check for existing claim in parent game =====
        from routes.poker_identity_claim_routes import get_existing_claim_for_game, get_claim_service
        from domain.poker.value_objects import PlayerId

        claim = get_existing_claim_for_game(db, str(current_user_id), str(live_game.game_id))

        if claim:
            # Auto-link to existing claimed player
            participant = service.join_live_game(
                live_game_id=live_game.id,
                user_id=current_user_id,
                display_name=display_name,
                player_id=PlayerId(str(claim.player_id))  # Link to claimed player
            )

            db.commit()

            # Broadcast SSE event
            broadcast_event(
                str(live_game.id),
                'participant_joined',
                {
                    'participant_id': str(participant.id),
                    'user_id': str(participant.user_id),
                    'display_name': participant.display_name,
                    'player_id': str(participant.player_id) if participant.player_id else None
                }
            )

            return jsonify({
                'participant_id': str(participant.id),
                'live_game_id': str(participant.live_game_id),
                'user_id': str(participant.user_id),
                'display_name': participant.display_name,
                'player_id': str(participant.player_id) if participant.player_id else None,
                'joined_at': participant.joined_at.isoformat(),
                'auto_linked': True,
                'player': {
                    'id': str(claim.player.id),
                    'name': claim.player.display_name  # CRITICAL: For success toast
                }
            }), 201

        # ===== STEP 3: No claim - fetch available players =====
        claim_service = get_claim_service(db)

        # Get parent game for lookup
        game = db.query(GameModel).filter(GameModel.id == str(live_game.game_id)).first()

        available_players = claim_service.get_claimable_players_in_game(
            GameId(str(game.id))
        )

        return jsonify({
            'needs_claim': True,
            'available_players': available_players
        }), 200

    except InvalidJoinCodeError as e:
        return jsonify({'error': str(e)}), 404

    except LiveGameNotFoundError as e:
        return jsonify({'error': str(e)}), 404

    except LiveGameAlreadyClosedError as e:
        return jsonify({'error': str(e)}), 410

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to join live game: {str(e)}'}), 500

    finally:
        db.close()


@live_game_bp.route('/live-games/<join_code>/claim-and-join', methods=['POST'])
@clerk_required
def claim_and_join_live_game(join_code):
    """
    Claim a player identity and join live game atomically.

    This endpoint handles the player identity claiming flow for live games.
    Users must claim a player identity before joining if they haven't already
    claimed one in the parent game.

    Request Body:
        {
            "player_id": "uuid",           // Optional - claim existing player
            "new_player_name": "string",   // Optional - create new player
            "display_name": "string"       // Required - game display name
        }

    Returns:
        201: {
            "participant_id": "uuid",
            "user_id": "uuid",
            "live_game_id": "uuid",
            "player_id": "uuid",
            "display_name": "John Doe",
            "joined_at": "2025-10-10T12:05:00Z",
            "player": {
                "id": "uuid",
                "name": "Player Name"
            }
        }

        400: { "error": "validation error message" }
            - Request body must be JSON
            - Provide either player_id or new_player_name, not both
            - Must provide either player_id or new_player_name
            - Display name is required
            - Display name must be 2-50 characters
            - Player name must be 2-50 characters
            - This player is not part of this game
            - This game is no longer accepting new players
        401: { "error": "authentication error" }
        404: { "error": "Player not found" | "Invalid or expired join code: XXXX" }
        409: { "error": "This player has already been claimed by another user" | "You have already joined this live game" }
        500: { "error": "server error message" }

    Validation:
        - Exactly one of player_id OR new_player_name must be provided
        - display_name is required (2-50 characters)
        - Player must be unclaimed (if player_id)
        - Live game must be active
    """
    db = SessionLocal()
    try:
        # ===== VALIDATION: Request Body =====
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        player_id_str = data.get('player_id')
        new_player_name = data.get('new_player_name', '').strip()
        display_name = data.get('display_name', '').strip()

        # Validate mutually exclusive
        if player_id_str and new_player_name:
            return jsonify({'error': 'Provide either player_id or new_player_name, not both'}), 400

        if not player_id_str and not new_player_name:
            return jsonify({'error': 'Must provide either player_id or new_player_name'}), 400

        # Validate display name
        if not display_name:
            return jsonify({'error': 'Display name is required'}), 400

        if len(display_name) < 2 or len(display_name) > 50:
            return jsonify({'error': 'Display name must be 2-50 characters'}), 400

        # Validate new player name (if creating)
        if new_player_name and (len(new_player_name) < 2 or len(new_player_name) > 50):
            return jsonify({'error': 'Player name must be 2-50 characters'}), 400

        # ===== GET LIVE GAME & VALIDATE =====
        service = get_live_game_service(db)
        live_game = service.get_live_game_by_join_code(join_code.strip().upper())

        if live_game.status != 'active':
            return jsonify({'error': 'This game is no longer accepting new players'}), 400

        current_user_id = UserId(str(get_current_user().id))

        # Check if already joined
        from db.models import LiveGameParticipant as LiveGameParticipantModel
        from db.models import Player as PlayerModel
        from db.models import GamePlayer as GamePlayerModel
        from db.models import PokerIdentityClaim as PokerIdentityClaimModel

        existing = db.query(LiveGameParticipantModel).filter(
            LiveGameParticipantModel.user_id == str(current_user_id),
            LiveGameParticipantModel.live_game_id == str(live_game.id)
        ).first()

        if existing:
            return jsonify({'error': 'You have already joined this live game'}), 409

        # ===== BRANCH: Claim Existing vs Create New =====
        claimed_player = None
        import uuid
        from datetime import datetime

        if player_id_str:
            # ===== Claim Existing Player =====
            player = db.query(PlayerModel).filter(PlayerModel.id == player_id_str).first()

            if not player:
                return jsonify({'error': 'Player not found'}), 404

            # Validate player belongs to parent game
            game_player = db.query(GamePlayerModel).filter(
                GamePlayerModel.player_id == player_id_str,
                GamePlayerModel.game_id == str(live_game.game_id)
            ).first()

            if not game_player:
                return jsonify({'error': 'This player is not part of this game'}), 400

            # Check if already claimed
            existing_claim = db.query(PokerIdentityClaimModel).filter(
                PokerIdentityClaimModel.player_id == player_id_str
            ).first()

            if existing_claim:
                return jsonify({'error': 'This player has already been claimed by another user'}), 409

            # Create claim
            claim = PokerIdentityClaimModel(
                id=uuid.uuid4(),
                user_id=str(current_user_id),
                player_id=player_id_str,
                claimed_at=datetime.utcnow(),
                verification_method='self_claim_live_game'
            )
            db.add(claim)
            claimed_player = player

        else:
            # ===== Create New Player =====
            new_player = PlayerModel(
                id=uuid.uuid4(),
                display_name=new_player_name,
                created_at=datetime.utcnow()
            )
            db.add(new_player)
            db.flush()  # Get ID for associations

            # Create GamePlayer association (link to PARENT game, not live game)
            game_player = GamePlayerModel(
                game_id=str(live_game.game_id),  # Parent game ID
                player_id=str(new_player.id),
                joined_at=datetime.utcnow()
            )
            db.add(game_player)

            # Create claim
            claim = PokerIdentityClaimModel(
                id=uuid.uuid4(),
                user_id=str(current_user_id),
                player_id=str(new_player.id),
                claimed_at=datetime.utcnow(),
                verification_method='self_claim_live_game'
            )
            db.add(claim)
            claimed_player = new_player

        # ===== CREATE PARTICIPANT =====
        from domain.poker.value_objects import PlayerId

        participant = service.join_live_game(
            live_game_id=live_game.id,
            user_id=current_user_id,
            display_name=display_name,
            player_id=PlayerId(str(claimed_player.id))
        )

        db.commit()

        # Broadcast SSE event
        broadcast_event(
            str(live_game.id),
            'participant_joined',
            {
                'participant_id': str(participant.id),
                'user_id': str(participant.user_id),
                'display_name': participant.display_name,
                'player_id': str(participant.player_id) if participant.player_id else None
            }
        )

        # ===== RESPONSE (matches auto-link structure) =====
        return jsonify({
            'participant_id': str(participant.id),
            'user_id': str(participant.user_id),
            'live_game_id': str(participant.live_game_id),
            'player_id': str(participant.player_id) if participant.player_id else None,
            'display_name': participant.display_name,
            'joined_at': participant.joined_at.isoformat(),
            'player': {
                'id': str(claimed_player.id),
                'name': claimed_player.display_name
            }
        }), 201

    except InvalidJoinCodeError as e:
        return jsonify({'error': str(e)}), 404

    except LiveGameNotFoundError as e:
        return jsonify({'error': str(e)}), 404

    except LiveGameAlreadyClosedError as e:
        return jsonify({'error': str(e)}), 410

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to claim and join: {str(e)}'}), 500

    finally:
        db.close()


@live_game_bp.route('/live-games/<join_code>', methods=['GET'])
def get_live_game(join_code):
    """
    Get live game details by join code.

    Path Parameters:
        join_code: 4-character join code (e.g., "A3B7")

    Returns:
        200: {
            "live_game_id": "uuid",
            "game_id": "uuid",
            "public_code": "ABC12",
            "join_code": "A3B7",
            "status": "active",
            "created_by_user_id": "uuid",
            "small_blind": 0.50,
            "big_blind": 1.00,
            "min_buy_in": 20.00,
            "max_buy_in": 100.00,
            "started_at": "2025-10-10T12:00:00Z",
            "closed_at": null
        }

        404: { "error": "Invalid or expired join code: XXXX" }
        410: { "error": "Cannot modify a closed live game" }
        500: { "error": "server error message" }
    """
    db = SessionLocal()
    try:
        service = get_live_game_service(db)
        live_game = service.get_live_game_by_join_code(join_code.strip().upper())

        # Get parent game's public code for admin session checks
        game = db.query(GameModel).filter(GameModel.id == str(live_game.game_id)).first()
        public_code = game.public_code if game else None

        return jsonify({
            'live_game_id': str(live_game.id),
            'game_id': str(live_game.game_id),
            'public_code': public_code,
            'join_code': live_game.join_code.value,
            'status': live_game.status,
            'created_by_user_id': str(live_game.created_by_user_id),
            'small_blind': float(live_game.small_blind) if live_game.small_blind else None,
            'big_blind': float(live_game.big_blind) if live_game.big_blind else None,
            'min_buy_in': float(live_game.min_buy_in),
            'max_buy_in': float(live_game.max_buy_in) if live_game.max_buy_in else None,
            'started_at': live_game.started_at.isoformat(),
            'closed_at': live_game.closed_at.isoformat() if live_game.closed_at else None
        }), 200

    except InvalidJoinCodeError as e:
        return jsonify({'error': str(e)}), 404

    except LiveGameNotFoundError as e:
        return jsonify({'error': str(e)}), 404

    except LiveGameAlreadyClosedError as e:
        return jsonify({'error': str(e)}), 410

    except Exception as e:
        return jsonify({'error': f'Failed to fetch live game: {str(e)}'}), 500

    finally:
        db.close()


@live_game_bp.route('/live-games/<join_code>/participants', methods=['GET'])
def get_participants(join_code):
    """
    Get all participants with current statistics.

    NOTE: This endpoint allows fetching participants even for closed games,
    as participant data is historical information that should remain accessible.

    Path Parameters:
        join_code: 4-character join code (e.g., "A3B7")

    Returns:
        200: {
            "participants": [
                {
                    "participant_id": "uuid",
                    "user_id": "uuid",
                    "display_name": "John Doe",
                    "joined_at": "2025-10-10T12:05:00Z",
                    "stats": {
                        "total_buy_ins": 100.00,
                        "total_cash_outs": 50.00,
                        "net_result": -50.00,
                        "chips_on_table": 50.00
                    }
                }
            ]
        }

        404: { "error": "Invalid or expired join code: XXXX" }
        500: { "error": "server error message" }
    """
    db = SessionLocal()
    try:
        service = get_live_game_service(db)

        # Get live game without validating active status (allow closed games)
        from domain.live_game.value_objects import JoinCode as JoinCodeVO
        try:
            join_code_vo = JoinCodeVO(join_code.strip().upper())
        except ValueError:
            return jsonify({'error': f'Invalid or expired join code: {join_code}'}), 404

        live_game = service.live_game_repo.get_by_join_code(join_code_vo)
        if not live_game:
            return jsonify({'error': f'Invalid or expired join code: {join_code}'}), 404

        # Get participants (works for both active and closed games)
        participants = service.get_participants(live_game.id)

        # Convert Decimal to float for JSON serialization
        for participant in participants:
            participant['stats'] = {
                'total_buy_ins': float(participant['stats']['total_buy_ins']),
                'total_cash_outs': float(participant['stats']['total_cash_outs']),
                'net_result': float(participant['stats']['net_result']),
                'chips_on_table': float(participant['stats']['chips_on_table'])
            }

        return jsonify({'participants': participants}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch participants: {str(e)}'}), 500

    finally:
        db.close()


# ============================================================================
# Transaction Management
# ============================================================================

@live_game_bp.route('/live-games/<join_code>/transactions/buy-in', methods=['POST'])
@clerk_required
def request_buy_in(join_code):
    """
    Request a buy-in transaction.

    Path Parameters:
        join_code: 4-character join code

    Request Body:
        {
            "amount": 50.00
        }

    Returns:
        201: {
            "transaction_id": "uuid",
            "live_game_id": "uuid",
            "participant_id": "uuid",
            "user_id": "uuid",
            "transaction_type": "buy_in",
            "amount": 50.00,
            "status": "pending",
            "created_at": "2025-10-10T12:10:00Z"
        }

        400: { "error": "validation error message" }
        401: { "error": "authentication error" }
        404: { "error": "Participant not found in this live game" }
        422: { "error": "Buy-in amount $5 must be at least $20" }
        500: { "error": "server error message" }
    """
    db = SessionLocal()
    try:
        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        if 'amount' not in data:
            return jsonify({'error': 'Missing required field: amount'}), 400

        try:
            amount = Decimal(str(data['amount']))
        except (InvalidOperation, ValueError):
            return jsonify({'error': 'Invalid amount: must be a valid number'}), 400

        # Get live game
        service = get_live_game_service(db)
        live_game = service.get_live_game_by_join_code(join_code.strip().upper())

        # Request buy-in
        current_user_id = UserId(str(get_current_user().id))
        transaction = service.request_buy_in(
            live_game_id=live_game.id,
            user_id=current_user_id,
            amount=amount
        )

        db.commit()

        # Get participant for display_name in SSE event
        participant_repo = SQLAlchemyParticipantRepository(db)
        participant = participant_repo.get_by_id(transaction.participant_id)

        # Broadcast SSE event
        broadcast_event(
            str(live_game.id),
            'transaction_created',
            {
                'transaction_id': str(transaction.id),
                'transaction_type': transaction.transaction_type,
                'participant_id': str(transaction.participant_id),
                'display_name': participant.display_name if participant else 'Unknown',
                'amount': float(transaction.amount),
                'status': transaction.status
            }
        )

        return jsonify({
            'transaction_id': str(transaction.id),
            'live_game_id': str(transaction.live_game_id),
            'participant_id': str(transaction.participant_id),
            'user_id': str(transaction.user_id),
            'transaction_type': transaction.transaction_type,
            'amount': float(transaction.amount),
            'status': transaction.status,
            'created_at': transaction.created_at.isoformat()
        }), 201

    except InvalidJoinCodeError as e:
        return jsonify({'error': str(e)}), 404

    except LiveGameNotFoundError as e:
        return jsonify({'error': str(e)}), 404

    except ParticipantNotFoundError as e:
        return jsonify({'error': str(e)}), 404

    except InvalidBuyInAmountError as e:
        return jsonify({'error': str(e)}), 422

    except LiveGameAlreadyClosedError as e:
        return jsonify({'error': str(e)}), 410

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to request buy-in: {str(e)}'}), 500

    finally:
        db.close()


@live_game_bp.route('/live-games/<join_code>/transactions/cash-out', methods=['POST'])
@clerk_required
def request_cash_out(join_code):
    """
    Request a cash-out transaction.

    Path Parameters:
        join_code: 4-character join code

    Request Body:
        {
            "amount": 75.00
        }

    Returns:
        201: {
            "transaction_id": "uuid",
            "live_game_id": "uuid",
            "participant_id": "uuid",
            "user_id": "uuid",
            "transaction_type": "cash_out",
            "amount": 75.00,
            "status": "pending",
            "created_at": "2025-10-10T12:30:00Z"
        }

        400: { "error": "validation error message" }
        401: { "error": "authentication error" }
        404: { "error": "Participant not found in this live game" }
        422: { "error": "Cannot cash out $100. You only have $75 in chips" }
        500: { "error": "server error message" }
    """
    db = SessionLocal()
    try:
        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        if 'amount' not in data:
            return jsonify({'error': 'Missing required field: amount'}), 400

        try:
            amount = Decimal(str(data['amount']))
        except (InvalidOperation, ValueError):
            return jsonify({'error': 'Invalid amount: must be a valid number'}), 400

        # Get live game
        service = get_live_game_service(db)
        live_game = service.get_live_game_by_join_code(join_code.strip().upper())

        # Request cash-out
        current_user_id = UserId(str(get_current_user().id))
        transaction = service.request_cash_out(
            live_game_id=live_game.id,
            user_id=current_user_id,
            amount=amount
        )

        db.commit()

        # Get participant for display_name in SSE event
        participant_repo = SQLAlchemyParticipantRepository(db)
        participant = participant_repo.get_by_id(transaction.participant_id)

        # Broadcast SSE event
        broadcast_event(
            str(live_game.id),
            'transaction_created',
            {
                'transaction_id': str(transaction.id),
                'transaction_type': transaction.transaction_type,
                'participant_id': str(transaction.participant_id),
                'display_name': participant.display_name if participant else 'Unknown',
                'amount': float(transaction.amount),
                'status': transaction.status
            }
        )

        return jsonify({
            'transaction_id': str(transaction.id),
            'live_game_id': str(transaction.live_game_id),
            'participant_id': str(transaction.participant_id),
            'user_id': str(transaction.user_id),
            'transaction_type': transaction.transaction_type,
            'amount': float(transaction.amount),
            'status': transaction.status,
            'created_at': transaction.created_at.isoformat()
        }), 201

    except InvalidJoinCodeError as e:
        return jsonify({'error': str(e)}), 404

    except LiveGameNotFoundError as e:
        return jsonify({'error': str(e)}), 404

    except ParticipantNotFoundError as e:
        return jsonify({'error': str(e)}), 404

    except InvalidCashOutAmountError as e:
        return jsonify({'error': str(e)}), 422

    except LiveGameAlreadyClosedError as e:
        return jsonify({'error': str(e)}), 410

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to request cash-out: {str(e)}'}), 500

    finally:
        db.close()


@live_game_bp.route('/live-games/<join_code>/transactions/pending', methods=['GET'])
@clerk_required
def get_pending_transactions(join_code):
    """
    Get all pending transactions for a live game.

    Requires admin permission (creator or admin session).

    Path Parameters:
        join_code: 4-character join code

    Returns:
        200: {
            "pending_transactions": [
                {
                    "transaction_id": "uuid",
                    "participant_id": "uuid",
                    "user_id": "uuid",
                    "transaction_type": "buy_in",
                    "amount": 50.00,
                    "status": "pending",
                    "created_at": "2025-10-10T12:10:00Z"
                }
            ]
        }

        401: { "error": "authentication error" }
        403: { "error": "You are not authorized to approve transactions for this live game" }
        404: { "error": "Invalid or expired join code: XXXX" }
        500: { "error": "server error message" }
    """
    db = SessionLocal()
    try:
        # Get live game
        service = get_live_game_service(db)
        live_game = service.get_live_game_by_join_code(join_code.strip().upper())

        # Check permission
        current_user_id = UserId(str(get_current_user().id))
        permission_service = get_permission_service(db)

        def admin_session_check(user_id: UserId, game_id: str) -> bool:
            return check_admin_session(db, user_id, game_id)

        permission_service.require_approval_permission(
            current_user_id,
            live_game.id,
            admin_session_check
        )

        # Get pending transactions
        transactions = service.get_pending_transactions(live_game.id)

        return jsonify({
            'pending_transactions': [
                {
                    'transaction_id': str(t.id),
                    'participant_id': str(t.participant_id),
                    'user_id': str(t.user_id),
                    'transaction_type': t.transaction_type,
                    'amount': float(t.amount),
                    'status': t.status,
                    'created_at': t.created_at.isoformat()
                }
                for t in transactions
            ]
        }), 200

    except InvalidJoinCodeError as e:
        return jsonify({'error': str(e)}), 404

    except LiveGameNotFoundError as e:
        return jsonify({'error': str(e)}), 404

    except UnauthorizedApprovalError as e:
        return jsonify({'error': str(e)}), 403

    except Exception as e:
        return jsonify({'error': f'Failed to fetch pending transactions: {str(e)}'}), 500

    finally:
        db.close()


@live_game_bp.route('/live-games/transactions/<transaction_id>/approve', methods=['PATCH'])
@clerk_required
def approve_transaction(transaction_id):
    """
    Approve a pending transaction.

    Requires admin permission (creator or admin session).

    Path Parameters:
        transaction_id: Transaction UUID

    Returns:
        200: {
            "transaction_id": "uuid",
            "status": "approved",
            "approved_by_user_id": "uuid",
            "approved_at": "2025-10-10T12:15:00Z"
        }

        401: { "error": "authentication error" }
        403: { "error": "You are not authorized to approve transactions for this live game" }
        404: { "error": "Transaction not found" }
        409: { "error": "Transaction is not pending" }
        500: { "error": "server error message" }
    """
    db = SessionLocal()
    try:
        service = get_live_game_service(db)
        current_user_id = UserId(str(get_current_user().id))

        # Get transaction to check live game
        transaction_repo = SQLAlchemyTransactionRepository(db)
        transaction = transaction_repo.get_by_id(TransactionId(transaction_id))

        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404

        # Check permission
        permission_service = get_permission_service(db)

        def admin_session_check(user_id: UserId, game_id: str) -> bool:
            return check_admin_session(db, user_id, game_id)

        permission_service.require_approval_permission(
            current_user_id,
            transaction.live_game_id,
            admin_session_check
        )

        # Approve transaction
        updated_transaction = service.approve_transaction(
            transaction_id=TransactionId(transaction_id),
            approved_by_user_id=current_user_id
        )

        db.commit()

        # Broadcast SSE event
        broadcast_event(
            str(transaction.live_game_id),
            'transaction_approved',
            {
                'transaction_id': str(updated_transaction.id),
                'participant_id': str(updated_transaction.participant_id),
                'transaction_type': updated_transaction.transaction_type,
                'amount': float(updated_transaction.amount),
                'approved_by_user_id': str(updated_transaction.approved_by_user_id)
            }
        )

        return jsonify({
            'transaction_id': str(updated_transaction.id),
            'status': updated_transaction.status,
            'approved_by_user_id': str(updated_transaction.approved_by_user_id),
            'approved_at': updated_transaction.approved_at.isoformat() if updated_transaction.approved_at else None
        }), 200

    except TransactionNotFoundError as e:
        return jsonify({'error': str(e)}), 404

    except TransactionNotPendingError as e:
        return jsonify({'error': str(e)}), 409

    except UnauthorizedApprovalError as e:
        return jsonify({'error': str(e)}), 403

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to approve transaction: {str(e)}'}), 500

    finally:
        db.close()


@live_game_bp.route('/live-games/transactions/<transaction_id>/reject', methods=['PATCH'])
@clerk_required
def reject_transaction(transaction_id):
    """
    Reject a pending transaction.

    Requires admin permission (creator or admin session).

    Path Parameters:
        transaction_id: Transaction UUID

    Request Body:
        {
            "reason": "Incorrect amount"
        }

    Returns:
        200: {
            "transaction_id": "uuid",
            "status": "rejected",
            "rejected_by_user_id": "uuid",
            "rejected_at": "2025-10-10T12:16:00Z",
            "rejection_reason": "Incorrect amount"
        }

        400: { "error": "Missing required field: reason" }
        401: { "error": "authentication error" }
        403: { "error": "You are not authorized to approve transactions for this live game" }
        404: { "error": "Transaction not found" }
        409: { "error": "Transaction is not pending" }
        500: { "error": "server error message" }
    """
    db = SessionLocal()
    try:
        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        if 'reason' not in data:
            return jsonify({'error': 'Missing required field: reason'}), 400

        reason = data['reason'].strip()
        if not reason:
            return jsonify({'error': 'Rejection reason cannot be empty'}), 400

        service = get_live_game_service(db)
        current_user_id = UserId(str(get_current_user().id))

        # Get transaction to check live game
        transaction_repo = SQLAlchemyTransactionRepository(db)
        transaction = transaction_repo.get_by_id(TransactionId(transaction_id))

        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404

        # Check permission
        permission_service = get_permission_service(db)

        def admin_session_check(user_id: UserId, game_id: str) -> bool:
            return check_admin_session(db, user_id, game_id)

        permission_service.require_approval_permission(
            current_user_id,
            transaction.live_game_id,
            admin_session_check
        )

        # Reject transaction
        updated_transaction = service.reject_transaction(
            transaction_id=TransactionId(transaction_id),
            rejected_by_user_id=current_user_id,
            reason=reason
        )

        db.commit()

        # Broadcast SSE event
        broadcast_event(
            str(transaction.live_game_id),
            'transaction_rejected',
            {
                'transaction_id': str(updated_transaction.id),
                'participant_id': str(updated_transaction.participant_id),
                'transaction_type': updated_transaction.transaction_type,
                'amount': float(updated_transaction.amount),
                'rejected_by_user_id': str(updated_transaction.approved_by_user_id),
                'rejection_reason': updated_transaction.notes
            }
        )

        return jsonify({
            'transaction_id': str(updated_transaction.id),
            'status': updated_transaction.status,
            'rejected_by_user_id': str(updated_transaction.approved_by_user_id),
            'rejected_at': updated_transaction.approved_at.isoformat() if updated_transaction.approved_at else None,
            'rejection_reason': updated_transaction.notes
        }), 200

    except TransactionNotFoundError as e:
        return jsonify({'error': str(e)}), 404

    except TransactionNotPendingError as e:
        return jsonify({'error': str(e)}), 409

    except UnauthorizedApprovalError as e:
        return jsonify({'error': str(e)}), 403

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to reject transaction: {str(e)}'}), 500

    finally:
        db.close()


@live_game_bp.route('/live-games/transactions/<transaction_id>', methods=['PATCH'])
@clerk_required
def edit_transaction(transaction_id):
    """
    Edit transaction amount (preserves original for audit).

    Requires admin permission (creator or admin session).

    Path Parameters:
        transaction_id: Transaction UUID

    Request Body:
        {
            "new_amount": 60.00,
            "reason": "Player requested correction"
        }

    Returns:
        200: {
            "transaction_id": "uuid",
            "amount": 60.00,
            "original_amount": 50.00,
            "edited_by_user_id": "uuid",
            "edited_at": "2025-10-10T12:20:00Z",
            "edit_reason": "Player requested correction"
        }

        400: { "error": "Missing required field: new_amount" }
        401: { "error": "authentication error" }
        403: { "error": "You are not authorized to approve transactions for this live game" }
        404: { "error": "Transaction not found" }
        500: { "error": "server error message" }
    """
    db = SessionLocal()
    try:
        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        if 'new_amount' not in data:
            return jsonify({'error': 'Missing required field: new_amount'}), 400
        if 'reason' not in data:
            return jsonify({'error': 'Missing required field: reason'}), 400

        try:
            new_amount = Decimal(str(data['new_amount']))
        except (InvalidOperation, ValueError):
            return jsonify({'error': 'Invalid new_amount: must be a valid number'}), 400

        reason = data['reason'].strip()
        if not reason:
            return jsonify({'error': 'Edit reason cannot be empty'}), 400

        service = get_live_game_service(db)
        current_user_id = UserId(str(get_current_user().id))

        # Get transaction to check live game
        transaction_repo = SQLAlchemyTransactionRepository(db)
        transaction = transaction_repo.get_by_id(TransactionId(transaction_id))

        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404

        # Check permission
        permission_service = get_permission_service(db)

        def admin_session_check(user_id: UserId, game_id: str) -> bool:
            return check_admin_session(db, user_id, game_id)

        permission_service.require_approval_permission(
            current_user_id,
            transaction.live_game_id,
            admin_session_check
        )

        # Edit transaction
        updated_transaction = service.edit_transaction_amount(
            transaction_id=TransactionId(transaction_id),
            new_amount=new_amount,
            edited_by_user_id=current_user_id,
            reason=reason
        )

        db.commit()

        # Broadcast SSE event
        broadcast_event(
            str(transaction.live_game_id),
            'transaction_edited',
            {
                'transaction_id': str(updated_transaction.id),
                'participant_id': str(updated_transaction.participant_id),
                'transaction_type': updated_transaction.transaction_type,
                'amount': float(updated_transaction.amount),
                'original_amount': float(updated_transaction.original_amount) if updated_transaction.original_amount else None,
                'edited_by_user_id': str(updated_transaction.edited_by_user_id),
                'edit_reason': updated_transaction.edit_reason
            }
        )

        return jsonify({
            'transaction_id': str(updated_transaction.id),
            'amount': float(updated_transaction.amount),
            'original_amount': float(updated_transaction.original_amount) if updated_transaction.original_amount else None,
            'edited_by_user_id': str(updated_transaction.edited_by_user_id),
            'edited_at': updated_transaction.edited_at.isoformat() if updated_transaction.edited_at else None,
            'edit_reason': updated_transaction.edit_reason
        }), 200

    except TransactionNotFoundError as e:
        return jsonify({'error': str(e)}), 404

    except UnauthorizedApprovalError as e:
        return jsonify({'error': str(e)}), 403

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to edit transaction: {str(e)}'}), 500

    finally:
        db.close()


# ============================================================================
# Game Closure
# ============================================================================

@live_game_bp.route('/live-games/<join_code>/close', methods=['POST'])
@clerk_required
def close_live_game(join_code):
    """
    Close a live game with validation and automatic session creation.

    Requires admin permission (creator or admin session).
    Validates:
    - All players have cashed out (no chips on table)
    - Game is balanced (total buy-ins = total cash-outs)

    NEW: Supports auto-handling busted players
    - If request includes "confirmed_zero_players", creates $0 cash-outs for those participants
    - If uncashed players exist and not confirmed, returns 409 with list for admin confirmation

    Automatically creates a session in the parent game's ledger if validation passes.
    Session creation happens atomically with game closure - if session creation
    fails, the game remains open.

    Path Parameters:
        join_code: 4-character join code

    Request Body (optional):
        {
            "confirmed_zero_players": ["participant_id_1", "participant_id_2"]
        }

    Returns:
        200: {
            "live_game_id": "uuid",
            "status": "closed",
            "closed_at": "2025-10-10T15:00:00Z",
            "summary": {
                "total_buy_ins": 500.00,
                "total_cash_outs": 500.00,
                "is_balanced": true
            },
            "session_created": true,          // NEW: whether session was created
            "session_id": "live_A3B7_1234",   // NEW: external session ID (if created)
            "game_number": 5                   // NEW: game number in ledger (if created)
        }

        401: { "error": "authentication error" }
        403: { "error": "You are not authorized to approve transactions for this live game" }
        404: { "error": "Invalid or expired join code: XXXX" }
        409: {
            "error": "Cannot close - N players haven't cashed out",
            "uncashed_players": [
                {
                    "participant_id": "uuid",
                    "display_name": "John Doe",
                    "total_buy_ins": 100.00,
                    "chips_on_table": 100.00
                }
            ]
        }
        422: { "error": "Game is not balanced. Total buy-ins: $500, Total cash-outs: $480, Difference: $20" }
        500: { "error": "server error message" }

    Note:
        If session creation fails, the game is still closed successfully.
        Use the recovery endpoint /live-games/<join_code>/create-session to
        manually create the session later.
    """
    db = SessionLocal()
    try:
        service = get_live_game_service(db)
        live_game = service.get_live_game_by_join_code(join_code.strip().upper())

        # Check permission
        current_user_id = UserId(str(get_current_user().id))
        permission_service = get_permission_service(db)

        def admin_session_check(user_id: UserId, game_id: str) -> bool:
            return check_admin_session(db, user_id, game_id)

        permission_service.require_approval_permission(
            current_user_id,
            live_game.id,
            admin_session_check
        )

        # Parse request for confirmed zero players
        data = request.get_json() or {}
        confirmed_zero_players = data.get('confirmed_zero_players', [])

        # If admin confirmed zero players, create $0 cash-outs for them
        if confirmed_zero_players:
            from domain.live_game.entities import LiveGameTransaction
            from domain.live_game.value_objects import ParticipantId

            for participant_id_str in confirmed_zero_players:
                participant_id = ParticipantId(participant_id_str)

                # Get participant to get user_id
                participant_repo = SQLAlchemyParticipantRepository(db)
                participant = participant_repo.get_by_id(participant_id)

                if participant:
                    # Create $0 cash-out transaction
                    transaction = LiveGameTransaction.create_cash_out(
                        live_game_id=live_game.id,
                        participant_id=participant.id,
                        user_id=participant.user_id,
                        amount=Decimal('0')
                    )
                    # Auto-approve it
                    transaction.approve(current_user_id)

                    # Save transaction
                    transaction_repo = SQLAlchemyTransactionRepository(db)
                    transaction_repo.create(transaction)

                    # Broadcast SSE event for transaction_approved
                    # (We skip transaction_created since it's immediately approved)
                    broadcast_event(
                        str(live_game.id),
                        'transaction_approved',
                        {
                            'transaction_id': str(transaction.id),
                            'participant_id': str(transaction.participant_id),
                            'transaction_type': transaction.transaction_type,
                            'amount': float(transaction.amount),
                            'approved_by_user_id': str(transaction.approved_by_user_id)
                        }
                    )

        # Try to close game (validates but doesn't commit yet)
        try:
            closed_game = service.close_live_game(live_game.id)
        except PlayersStillActiveError:
            # Get uncashed players for confirmation
            participants = service.get_participants(live_game.id)
            uncashed_players = []

            for p in participants:
                if not p['stats'].get('has_cashed_out', False):
                    uncashed_players.append({
                        'participant_id': p['participant_id'],
                        'display_name': p['display_name'],
                        'total_buy_ins': float(p['stats']['total_buy_ins']),
                        'chips_on_table': float(p['stats']['chips_on_table'])
                    })

            # Rollback any uncommitted changes
            db.rollback()

            # Return error with uncashed players list for confirmation
            return jsonify({
                'error': f'Cannot close - {len(uncashed_players)} player(s) haven\'t cashed out',
                'uncashed_players': uncashed_players
            }), 409

        # Create session from live game (ATOMIC - same transaction)
        # If this fails, the game closure will be rolled back
        session_result = None
        try:
            session_result = service.create_session_from_live_game(live_game.id, db)
        except Exception as session_error:
            # Log the error but don't fail the close operation
            # Session creation will be available via recovery endpoint
            import logging
            log = logging.getLogger(__name__)
            log.error(f"Failed to create session from live game {join_code}: {session_error}")
            # Continue without session creation

        # Commit both operations together
        db.commit()

        # Get summary
        summary = service.get_game_summary(live_game.id)

        # Broadcast SSE event (game closed - disconnects all clients)
        broadcast_event(
            str(live_game.id),
            'game_closed',
            {
                'live_game_id': str(closed_game.id),
                'closed_at': closed_game.closed_at.isoformat() if closed_game.closed_at else None,
                'total_buy_ins': summary['total_buy_ins'],
                'total_cash_outs': summary['total_cash_outs'],
                'is_balanced': summary['is_balanced'],
                'session_created': session_result is not None,
                'session_id': session_result['session_id'] if session_result else None,
                'game_number': session_result['game_number'] if session_result else None
            }
        )

        response_data = {
            'live_game_id': str(closed_game.id),
            'status': closed_game.status,
            'closed_at': closed_game.closed_at.isoformat() if closed_game.closed_at else None,
            'summary': {
                'total_buy_ins': summary['total_buy_ins'],
                'total_cash_outs': summary['total_cash_outs'],
                'is_balanced': summary['is_balanced']
            }
        }

        # Include session info if created
        if session_result:
            response_data['session_created'] = True
            response_data['session_id'] = session_result['session_id']
            response_data['game_number'] = session_result['game_number']

        return jsonify(response_data), 200

    except InvalidJoinCodeError as e:
        return jsonify({'error': str(e)}), 404

    except LiveGameNotFoundError as e:
        return jsonify({'error': str(e)}), 404

    except UnauthorizedApprovalError as e:
        return jsonify({'error': str(e)}), 403

    except PlayersStillActiveError as e:
        return jsonify({'error': str(e)}), 409

    except GameNotBalancedError as e:
        return jsonify({'error': str(e)}), 422

    except LiveGameAlreadyClosedError as e:
        return jsonify({'error': str(e)}), 410

    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to close live game: {str(e)}'}), 500

    finally:
        db.close()


@live_game_bp.route('/live-games/<join_code>/create-session', methods=['POST'])
@clerk_required
def create_session_from_closed_game(join_code):
    """
    Manually create a session from a closed live game.

    This endpoint provides error recovery for cases where automatic session
    creation failed during game closure. Can only be used on closed games
    that don't already have a session created.

    Requires admin permission (creator or admin session).

    Path Parameters:
        join_code: 4-character join code

    Returns:
        200: {
            "success": true,
            "session_id": "live_A3B7_1234",
            "game_number": 5,
            "players_processed": 3
        }

        400: { "error": "Game is not closed" }
        401: { "error": "authentication error" }
        403: { "error": "You are not authorized to manage this live game" }
        404: { "error": "Invalid or expired join code: XXXX" }
        409: { "error": "Session already exists for this live game" }
        500: { "error": "server error message" }
    """
    db = SessionLocal()
    try:
        service = get_live_game_service(db)

        # Get live game (allow closed games)
        from domain.live_game.value_objects import JoinCode as JoinCodeVO
        join_code_vo = JoinCodeVO(join_code.strip().upper())
        live_game = service.live_game_repo.get_by_join_code(join_code_vo)

        if not live_game:
            return jsonify({'error': f'Invalid or expired join code: {join_code}'}), 404

        # Check permission
        current_user_id = UserId(str(get_current_user().id))
        permission_service = get_permission_service(db)

        def admin_session_check(user_id: UserId, game_id: str) -> bool:
            return check_admin_session(db, user_id, game_id)

        permission_service.require_approval_permission(
            current_user_id,
            live_game.id,
            admin_session_check
        )

        # Validate game is closed
        if live_game.status != 'closed':
            return jsonify({'error': 'Game must be closed before creating a session'}), 400

        # Check if session already exists
        from db.models import Session as SessionModel
        external_id = f"live_{live_game.join_code.value}_{int(live_game.started_at.timestamp())}"
        existing_session = db.query(SessionModel).filter(
            SessionModel.external_id == external_id
        ).first()

        if existing_session:
            return jsonify({
                'error': 'Session already exists for this live game',
                'session_id': existing_session.external_id,
                'game_number': existing_session.game_number
            }), 409

        # Create session
        session_result = service.create_session_from_live_game(live_game.id, db)
        db.commit()

        return jsonify({
            'success': True,
            'session_id': session_result['session_id'],
            'game_number': session_result['game_number'],
            'players_processed': session_result['players_processed'],
            'live_game_id': session_result['live_game_id'],
            'join_code': session_result['join_code']
        }), 200

    except UnauthorizedApprovalError as e:
        return jsonify({'error': str(e)}), 403

    except Exception as e:
        db.rollback()
        import logging
        log = logging.getLogger(__name__)
        log.error(f"Failed to create session from closed game {join_code}: {e}")
        return jsonify({'error': f'Failed to create session: {str(e)}'}), 500

    finally:
        db.close()


@live_game_bp.route('/live-games/<join_code>/summary', methods=['GET'])
def get_game_summary(join_code):
    """
    Get complete game summary for reconciliation.

    Path Parameters:
        join_code: 4-character join code

    Returns:
        200: {
            "live_game_id": "uuid",
            "status": "active",
            "started_at": "2025-10-10T12:00:00Z",
            "closed_at": null,
            "total_buy_ins": 500.00,
            "total_cash_outs": 450.00,
            "difference": 50.00,
            "is_balanced": false,
            "participants": [
                {
                    "display_name": "John Doe",
                    "stats": {
                        "total_buy_ins": 100.00,
                        "total_cash_outs": 50.00,
                        "net_result": -50.00,
                        "chips_on_table": 50.00
                    }
                }
            ]
        }

        404: { "error": "Invalid or expired join code: XXXX" }
        500: { "error": "server error message" }
    """
    db = SessionLocal()
    try:
        service = get_live_game_service(db)
        live_game = service.get_live_game_by_join_code(join_code.strip().upper())

        summary = service.get_game_summary(live_game.id)

        # Convert Decimal to float for JSON serialization
        for participant in summary['participants']:
            participant['stats'] = {
                'total_buy_ins': float(participant['stats']['total_buy_ins']),
                'total_cash_outs': float(participant['stats']['total_cash_outs']),
                'net_result': float(participant['stats']['net_result']),
                'chips_on_table': float(participant['stats']['chips_on_table'])
            }

        return jsonify(summary), 200

    except InvalidJoinCodeError as e:
        return jsonify({'error': str(e)}), 404

    except LiveGameNotFoundError as e:
        return jsonify({'error': str(e)}), 404

    except Exception as e:
        return jsonify({'error': f'Failed to fetch game summary: {str(e)}'}), 500

    finally:
        db.close()
