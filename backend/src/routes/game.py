from sqlalchemy import text
from db.database import SessionLocal
from flask import Blueprint, request, jsonify
import logging
from services.transaction_service import get_game_transactions
from services.session_ingestion_service import ingest_session
from services.game_summary_service import get_player_summaries, get_player_analytics, get_session_extremes
from services.ledger_service import (
    get_all_session_summaries,
    get_session_summary,
    update_session_summary,
    delete_session_summary,
    delete_entire_session
)
from services.player_verification_service import (
    get_unverified_players,
    verify_player,
    update_verified_player,
    get_player_details,
    get_player_verification_debug
)
from services.player_merge_service import (
    find_potential_duplicates,
    merge_players
)
from services.audit_service import (
    get_merge_audit_logs,
    get_all_audit_logs,
    undo_player_merge,
    get_operation_details
)
from services.ledger_analysis_service import get_ledger_analysis
from services.audit_middleware import audit_context
from services.live_game_service import (
    validate_live_game_data,
    create_live_game_session_data,
    validate_session_balance
)
from services.game_creation_service import (
    create_game,
    validate_game_title
)
from services.payment_service import PaymentService
from services.audit_middleware import audit_context
from decimal import Decimal
from datetime import timezone, datetime
from sqlalchemy import func
from db.models import Game, Player, PaymentTransaction, PaymentBalance, Session as SessionModel, SessionPlayerSummary, GamePlayer, AuditLog

game_bp = Blueprint('game', __name__)

logging.basicConfig(level=logging.DEBUG)

@game_bp.route('/create', methods=['POST'])
def create_new_game():
    """
    Create a new game with generated codes.
    
    Body expects:
    {
      "title": "My Poker Game"  // optional
    }
    
    Returns:
    {
      "game_id": "uuid",
      "public_code": "ABC123", 
      "admin_code": "long-secret-token",
      "title": "My Poker Game",
      "created_at": "2025-01-15T10:30:00Z"
    }
    """
    try:
        body = request.get_json() or {}
        title = body.get("title")
        
        # Validate title if provided
        if title is not None:
            try:
                title = validate_game_title(title)
            except ValueError as ve:
                return jsonify({"error": f"Invalid title: {str(ve)}"}), 400
        
        # Create the game
        result = create_game(title=title)
        
        return jsonify(result), 201
        
    except RuntimeError as e:
        logging.error(f"Game creation failed: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logging.exception("Unexpected error in /create")
        return jsonify({"error": "Internal server error"}), 500

@game_bp.route('/get_transactions', methods=['GET'])
def get_transactions():
    base_url = request.args.get('url')
    if base_url:
        base_url = base_url.strip()
    logging.debug(f"Received base_url: {base_url}")
    if not base_url:
        logging.error("URL parameter is missing")
        return jsonify({'error': 'URL parameter is missing'}), 400
    try:
        data = get_game_transactions(base_url)
        return jsonify(data), 200
    except Exception as e:
        logging.error(f"Error in get_game_transactions: {e}")
        return jsonify({'error': str(e)}), 500

@game_bp.route('/upload', methods=['POST'])
def upload_dual():
    """
    Body expects:
    {
      "public_code": "C4QROK",
      "sessionId": "pokernow-session-id-123",      # required
      "game_data": { ... PokerNow players_sessions-like payload ... },
      "date": "2025-08-11T00:00:00",               # optional; uses 'today' if omitted
      "gameNumber": 81                             # optional; manual override for game number
    }
    Header: X-Admin-Code: <admin_code>
    """
    try:
        body = request.get_json(force=True)
        public_code = body.get("public_code")
        session_id = body.get("sessionId")
        game_data = body.get("game_data") or {}
        date_iso = body.get("date")
        game_number = body.get("gameNumber")  # Optional manual override

        if not public_code:
            return jsonify({"error": "public_code is required"}), 400
        if not session_id:
            return jsonify({"error": "sessionId is required"}), 400

        admin_code = request.headers.get("X-Admin-Code")
        if not admin_code:
            return jsonify({"error": "X-Admin-Code header required"}), 401

        result = ingest_session(
            public_code=public_code,
            admin_code=admin_code,
            session_id=session_id,
            game_data=game_data,
            date_iso=date_iso,
            manual_game_number=game_number,
        )
        return jsonify(result), 200

    except PermissionError as e:
        logging.error(f"Unauthorized: {e}")
        return jsonify({"error": str(e)}), 401
    except ValueError as e:
        logging.error(f"Bad request: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.exception("Unexpected error in /upload")
        return jsonify({"error": "Internal server error"}), 500

@game_bp.route('/upload_live', methods=['POST'])
def upload_live_game():
    """
    Upload live game results.
    
    Body expects:
    {
      "public_code": "C4QROK",
      "session_name": "Thursday Night Game #15",
      "players": [
        {"name": "Alice", "buy_in": 100.00, "cash_out": 150.00, "in_game": 0.00},
        {"name": "Bob", "buy_in": 100.00, "cash_out": 80.00, "in_game": 0.00}
      ],
      "date": "2025-08-11T00:00:00",               # optional; uses 'now' if omitted
      "gameNumber": 15                             # optional; manual override for game number
    }
    Header: X-Admin-Code: <admin_code>
    """
    try:
        body = request.get_json(force=True)
        public_code = body.get("public_code")
        session_name = body.get("session_name")
        players_data = body.get("players", [])
        date_iso = body.get("date")
        game_number = body.get("gameNumber")

        if not public_code:
            return jsonify({"error": "public_code is required"}), 400
        if not session_name:
            return jsonify({"error": "session_name is required"}), 400
        if not players_data or not isinstance(players_data, list):
            return jsonify({"error": "players array is required"}), 400

        admin_code = request.headers.get("X-Admin-Code")
        if not admin_code:
            return jsonify({"error": "X-Admin-Code header required"}), 401

        # Validate player data
        try:
            validated_players = validate_live_game_data(players_data)
        except ValueError as ve:
            logging.error(f"Invalid player data: {ve}")
            return jsonify({"error": f"Invalid player data: {str(ve)}"}), 400

        # Validate session balance
        balance_validation = validate_session_balance(validated_players)
        
        # Create session data in PokerNow-compatible format
        from datetime import datetime, timezone
        session_date = None
        if date_iso:
            try:
                session_date = datetime.fromisoformat(date_iso.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"error": "Invalid date format"}), 400
        else:
            session_date = datetime.now(timezone.utc)

        live_session_data = create_live_game_session_data(
            session_name=session_name,
            players_data=validated_players,
            session_date=session_date
        )

        # Use existing dual_write_service with live game data
        result = ingest_session(
            public_code=public_code,
            admin_code=admin_code,
            session_id=live_session_data["sessionId"],
            game_data=live_session_data,
            date_iso=date_iso,
            manual_game_number=game_number,
            session_type="live"  # Add this parameter to distinguish live games
        )
        
        # Add balance validation info to result
        result["balance_validation"] = balance_validation
        
        return jsonify(result), 200

    except PermissionError as e:
        logging.error(f"Unauthorized: {e}")
        return jsonify({"error": str(e)}), 401
    except ValueError as e:
        logging.error(f"Bad request: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.exception("Unexpected error in /upload_live")
        return jsonify({"error": "Internal server error"}), 500

@game_bp.get("/<public_code>/summary")
def players_summary(public_code: str):
    result = get_player_summaries(public_code)
    title = result.get("title")
    rows = result.get("rows", [])
    return jsonify({"game": public_code, "title": title, "rows": rows})

@game_bp.get("/<public_code>/analytics")
def players_analytics(public_code: str):
    """
    Get advanced player analytics including streak calculations.
    """
    try:
        result = get_player_analytics(public_code)
        return jsonify(result)
    except Exception as e:
        logging.error(f"Error fetching player analytics: {e}")
        return jsonify({"error": "Failed to fetch analytics"}), 500

@game_bp.get("/<public_code>/session-extremes")
def players_session_extremes(public_code: str):
    """
    Get the actual best and worst single session performances.
    """
    try:
        result = get_session_extremes(public_code)
        return jsonify(result)
    except Exception as e:
        logging.error(f"Error fetching session extremes: {e}")
        return jsonify({"error": "Failed to fetch session extremes"}), 500

@game_bp.get("/<public_code>/ledger")
def get_ledger(public_code: str):
    """
    Get all SessionPlayerSummary records for a game.
    Returns detailed ledger data for admin view.
    """
    try:
        result = get_all_session_summaries(public_code)
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error fetching ledger: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.get("/<public_code>/ledger/<session_id>/<player_id>")
def get_ledger_entry(public_code: str, session_id: str, player_id: str):
    """
    Get a single SessionPlayerSummary record.
    """
    try:
        result = get_session_summary(session_id, player_id)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logging.error(f"Error fetching ledger entry: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.put("/<public_code>/ledger/<session_id>/<player_id>")
def update_ledger_entry(public_code: str, session_id: str, player_id: str):
    """
    Update a SessionPlayerSummary record.
    Body expects:
    {
      "buy_in_sum": 1000,
      "cash_out_sum": 1200,
      "in_game": 0,
      "net": 200,
      "names": ["Player Name", "Alternative Name"]
    }
    Note: player_id is taken from URL path, not request body
    Header: X-Admin-Code: <admin_code>
    """
    try:
        admin_code = request.headers.get("X-Admin-Code")
        if not admin_code:
            return jsonify({"error": "X-Admin-Code header required"}), 401

        # Get game for audit context
        from services.session_ingestion_service import _require_admin_for_game
        with SessionLocal() as db:
            game = _require_admin_for_game(db, public_code, admin_code)
        
        body = request.get_json(force=True)
        if not body:
            return jsonify({"error": "Request body is required"}), 400

        # Set audit context for this operation
        with audit_context(
            operation_type="LEDGER_UPDATE",
            game_id=str(game.id),
            actor_kind="admin_code",
            actor_id=admin_code[:8] + "…"
        ):
            result = update_session_summary(session_id, player_id, body)
        return jsonify(result), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.error(f"Error updating ledger entry: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.delete("/<public_code>/ledger/<session_id>/<player_id>")
def delete_ledger_entry(public_code: str, session_id: str, player_id: str):
    """
    Delete a SessionPlayerSummary record.
    Note: player_id is taken from URL path
    Header: X-Admin-Code: <admin_code>
    """
    try:
        admin_code = request.headers.get("X-Admin-Code")
        if not admin_code:
            return jsonify({"error": "X-Admin-Code header required"}), 401

        # Get game for audit context
        from services.session_ingestion_service import _require_admin_for_game
        with SessionLocal() as db:
            game = _require_admin_for_game(db, public_code, admin_code)

        # Set audit context for this operation
        with audit_context(
            operation_type="LEDGER_DELETE",
            game_id=str(game.id),
            actor_kind="admin_code",
            actor_id=admin_code[:8] + "…"
        ):
            result = delete_session_summary(session_id, player_id)
        return jsonify(result), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logging.error(f"Error deleting ledger entry: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.delete("/<public_code>/sessions/<session_id>")
def delete_entire_session_route(public_code: str, session_id: str):
    """
    Delete an entire session including all player summaries.
    Header: X-Admin-Code: <admin_code>
    """
    try:
        admin_code = request.headers.get("X-Admin-Code")
        if not admin_code:
            return jsonify({"error": "X-Admin-Code header required"}), 401

        # Get game for audit context
        from services.session_ingestion_service import _require_admin_for_game
        with SessionLocal() as db:
            game = _require_admin_for_game(db, public_code, admin_code)

        # Set audit context for this operation
        with audit_context(
            operation_type="SESSION_DELETE",
            game_id=str(game.id),
            actor_kind="admin_code",
            actor_id=admin_code[:8] + "…"
        ):
            result = delete_entire_session(session_id)
        return jsonify(result), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logging.error(f"Error deleting entire session: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.get("/<public_code>/players/verification")
def get_player_verification_data(public_code: str):
    """
    Get unverified and verified players for the verification page.
    """
    try:
        result = get_unverified_players(public_code)
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error fetching player verification data: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.get("/<public_code>/players/verification-debug")
def get_player_verification_debug_data(public_code: str):
    """
    Get comprehensive debugging information about player verification issues.
    Identifies duplicate names, external ID conflicts, and other issues.
    """
    try:
        result = get_player_verification_debug(public_code)
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error fetching player verification debug data: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.get("/<public_code>/players/<player_id>/details")
def get_player_detail(public_code: str, player_id: str):
    """
    Get detailed information about a specific player.
    """
    try:
        result = get_player_details(player_id)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logging.error(f"Error fetching player details: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.post("/<public_code>/players/<player_id>/verify")
def verify_player_name(public_code: str, player_id: str):
    """
    Verify a player by setting their verified name.
    Body expects:
    {
      "verified_name": "John Doe"
    }
    Header: X-Admin-Code: <admin_code>
    """
    try:
        admin_code = request.headers.get("X-Admin-Code")
        if not admin_code:
            return jsonify({"error": "X-Admin-Code header required"}), 401

        body = request.get_json(force=True)
        if not body or not body.get("verified_name"):
            return jsonify({"error": "verified_name is required"}), 400

        result = verify_player(player_id, body["verified_name"], body.get("external_id"))
        return jsonify(result), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.error(f"Error verifying player: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.put("/<public_code>/players/<player_id>/verify")
def update_verified_player_name(public_code: str, player_id: str):
    """
    Update an already verified player's name.
    Body expects:
    {
      "verified_name": "John Doe"
    }
    Header: X-Admin-Code: <admin_code>
    """
    try:
        admin_code = request.headers.get("X-Admin-Code")
        if not admin_code:
            return jsonify({"error": "X-Admin-Code header required"}), 401

        body = request.get_json(force=True)
        if not body or not body.get("verified_name"):
            return jsonify({"error": "verified_name is required"}), 400

        result = update_verified_player(player_id, body["verified_name"], body.get("external_id"))
        return jsonify(result), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.error(f"Error updating verified player: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.post("/<public_code>/players/find-duplicates")
def find_player_duplicates(public_code: str):
    """
    Find potential duplicate players for a given verified name.
    Body expects:
    {
      "verified_name": "John Doe",
      "exclude_player_id": "uuid" // optional - exclude this player from search
    }
    """
    try:
        body = request.get_json(force=True)
        if not body or not body.get("verified_name"):
            return jsonify({"error": "verified_name is required"}), 400

        result = find_potential_duplicates(
            public_code=public_code,
            verified_name=body["verified_name"],
            exclude_player_id=body.get("exclude_player_id")
        )
        return jsonify(result), 200

    except Exception as e:
        logging.error(f"Error finding duplicates: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.post("/<public_code>/players/merge")
def merge_duplicate_players(public_code: str):
    """
    Merge multiple players into one verified player.
    Body expects:
    {
      "target_player_id": "uuid",
      "source_player_ids": ["uuid1", "uuid2"],
      "verified_name": "John Doe",
      "external_id": "pokernow_123" // optional
    }
    Header: X-Admin-Code: <admin_code>
    """
    try:
        admin_code = request.headers.get("X-Admin-Code")
        if not admin_code:
            return jsonify({"error": "X-Admin-Code header required"}), 401

        body = request.get_json(force=True)
        if not body:
            return jsonify({"error": "Request body is required"}), 400
        
        required_fields = ["target_player_id", "source_player_ids", "verified_name"]
        for field in required_fields:
            if not body.get(field):
                return jsonify({"error": f"{field} is required"}), 400

        # Get game for audit logging
        from services.session_ingestion_service import _require_admin_for_game
        with SessionLocal() as db:
            game = _require_admin_for_game(db, public_code, admin_code)
        
        result = merge_players(
            target_player_id=body["target_player_id"],
            source_player_ids=body["source_player_ids"],
            verified_name=body["verified_name"],
            external_id=body.get("external_id"),
            admin_code=admin_code,
            game_id=str(game.id)
        )
        return jsonify(result), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.error(f"Error merging players: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.get("/<public_code>/audit")
def get_game_all_audits(public_code: str):
    """
    Get all audit logs for a specific game.
    Query params:
    - limit: number of entries to return (default 50)
    - offset: pagination offset (default 0)
    """
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        result = get_all_audit_logs(
            public_code=public_code,
            limit=limit,
            offset=offset
        )
        return jsonify(result), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logging.error(f"Error fetching all audits: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.get("/<public_code>/audit/merges")
def get_game_merge_audits(public_code: str):
    """
    Get merge audit logs for a specific game.
    Query params:
    - limit: number of entries to return (default 20)
    """
    try:
        limit = int(request.args.get('limit', 20))
        
        result = get_merge_audit_logs(
            public_code=public_code,
            limit=limit
        )
        return jsonify(result), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logging.error(f"Error fetching merge audits: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.get("/<public_code>/audit/operation/<operation_id>")
def get_audit_operation_details(public_code: str, operation_id: str):
    """
    Get detailed information about a specific operation.
    """
    try:
        result = get_operation_details(operation_id)
        return jsonify(result), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logging.error(f"Error fetching operation details: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.post("/<public_code>/audit/undo/<operation_id>")
def undo_merge_operation(public_code: str, operation_id: str):
    """
    Undo a merge operation.
    Header: X-Admin-Code: <admin_code>
    """
    try:
        admin_code = request.headers.get("X-Admin-Code")
        if not admin_code:
            return jsonify({"error": "X-Admin-Code header required"}), 401

        # Validate admin code for this game
        from services.session_ingestion_service import _require_admin_for_game
        with SessionLocal() as db:
            game = _require_admin_for_game(db, public_code, admin_code)
        
        result = undo_player_merge(
            operation_id=operation_id,
            admin_code=admin_code
        )
        return jsonify(result), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.error(f"Error undoing merge operation: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.get("/<public_code>/ledger-analysis")
def get_game_ledger_analysis(public_code: str):
    """
    Get comprehensive ledger analysis for a specific game.
    Analyzes balance discrepancies and identifies potential problems.
    """
    try:
        result = get_ledger_analysis(public_code)
        return jsonify(result), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logging.error(f"Error fetching ledger analysis: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.get("/<public_code>/sessions/<session_id>/detail")
def get_session_detail(public_code: str, session_id: str):
    """
    Get detailed information about a specific session including player breakdown.
    """
    try:
        from services.ledger_analysis_service import get_session_detail
        result = get_session_detail(session_id)
        return jsonify(result), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logging.error(f"Error fetching session detail: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.post("/<public_code>/sessions/<session_id>/recalculate")
def recalculate_session_balance(public_code: str, session_id: str):
    """
    Recalculate session balance by re-summing all player entries.
    Header: X-Admin-Code: <admin_code>
    """
    try:
        admin_code = request.headers.get("X-Admin-Code")
        if not admin_code:
            return jsonify({"error": "X-Admin-Code header required"}), 401

        # Get game for audit context
        from services.session_ingestion_service import _require_admin_for_game
        with SessionLocal() as db:
            game = _require_admin_for_game(db, public_code, admin_code)
        
        # Set audit context for this operation
        with audit_context(
            operation_type="SESSION_RECALCULATE",
            game_id=str(game.id),
            actor_kind="admin_code",
            actor_id=admin_code[:8] + "…"
        ):
            from services.ledger_analysis_service import recalculate_session_balance as recalc_service
            result = recalc_service(session_id)
        return jsonify(result), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.error(f"Error recalculating session balance: {e}")
        return jsonify({"error": str(e)}), 500


# ==========================================================
# Payment Ledger Endpoints
# ==========================================================

payment_service = PaymentService()

@game_bp.get("/<public_code>/payments/summary")
def get_payment_summary(public_code: str):
    """
    Get payment summary for all players in the game.
    Returns current balances and payment status.
    """
    try:
        # Get game by public code
        with SessionLocal() as db:
            game = db.query(Game).filter(Game.public_code == public_code).first()
            if not game:
                return jsonify({"error": "Game not found"}), 404
            
            summary = payment_service.get_payment_summary(str(game.id))
            
            # Convert to JSON-serializable format
            result = []
            for player_summary in summary:
                result.append({
                    "player_id": player_summary.player_id,
                    "player_name": player_summary.player_name,
                    "poker_net_winnings": float(player_summary.poker_net_winnings),
                    "total_paid": float(player_summary.total_paid),
                    "total_received": float(player_summary.total_received),
                    "balance": float(player_summary.balance),
                    "realized_earnings": float(player_summary.realized_earnings)
                })
            
            return jsonify({"players": result}), 200
            
    except Exception as e:
        logging.error(f"Error getting payment summary: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.get("/<public_code>/payments/settlements")
def get_settlement_suggestions(public_code: str):
    """
    Get optimal settlement suggestions to minimize transactions.
    """
    try:
        # Get game by public code
        with SessionLocal() as db:
            game = db.query(Game).filter(Game.public_code == public_code).first()
            if not game:
                return jsonify({"error": "Game not found"}), 404
            
            suggestions = payment_service.get_settlement_suggestions(str(game.id))
            
            # Convert to JSON-serializable format
            result = []
            for suggestion in suggestions:
                result.append({
                    "payer_id": suggestion.payer_id,
                    "payer_name": suggestion.payer_name,
                    "recipient_id": suggestion.recipient_id,
                    "recipient_name": suggestion.recipient_name,
                    "amount": float(suggestion.amount)
                })
            
            return jsonify({"settlements": result}), 200
            
    except Exception as e:
        logging.error(f"Error getting settlement suggestions: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.get("/<public_code>/payments/history")
def get_payment_history(public_code: str):
    """
    Get payment transaction history for the game.
    Query params:
    - limit: number of transactions to return (default 1000)
    - offset: pagination offset (default 0)
    """
    try:
        limit = int(request.args.get('limit', 1000))
        offset = int(request.args.get('offset', 0))
        
        # Get game by public code
        with SessionLocal() as db:
            game = db.query(Game).filter(Game.public_code == public_code).first()
            if not game:
                return jsonify({"error": "Game not found"}), 404
            
            history = payment_service.get_payment_history(
                str(game.id), 
                limit=limit, 
                offset=offset
            )
            
            return jsonify({"transactions": history}), 200
            
    except Exception as e:
        logging.error(f"Error getting payment history: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.post("/<public_code>/payments/record")
def record_payment_transaction(public_code: str):
    """
    Record a payment between two players (admin only).
    
    Body expects:
    {
      "payer_id": "uuid",
      "recipient_id": "uuid", 
      "amount": 125.50,
      "payment_date": "2025-09-03T10:30:00Z",  // optional, defaults to now
      "payment_method": "Venmo",               // optional
      "notes": "Weekly settlement",            // optional
      "reference_id": "venmo_12345"            // optional
    }
    Header: X-Admin-Code: <admin_code>
    """
    try:
        admin_code = request.headers.get("X-Admin-Code")
        if not admin_code:
            return jsonify({"error": "X-Admin-Code header required"}), 401

        # Get game and validate admin access
        from services.session_ingestion_service import _require_admin_for_game
        with SessionLocal() as db:
            game = _require_admin_for_game(db, public_code, admin_code)

        body = request.get_json(force=True)
        if not body:
            return jsonify({"error": "Request body is required"}), 400

        # Validate required fields
        required_fields = ["payer_id", "recipient_id", "amount"]
        for field in required_fields:
            if field not in body:
                return jsonify({"error": f"{field} is required"}), 400

        # Parse payment date
        from datetime import datetime
        payment_date = datetime.now(timezone.utc)
        if "payment_date" in body and body["payment_date"]:
            try:
                payment_date = datetime.fromisoformat(body["payment_date"].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"error": "Invalid payment_date format"}), 400

        # Set audit context
        with audit_context(
            operation_type="PAYMENT_RECORD",
            game_id=str(game.id),
            actor_kind="admin_code",
            actor_id=admin_code[:8] + "…"
        ):
            payment = payment_service.record_payment(
                game_id=str(game.id),
                payer_id=body["payer_id"],
                recipient_id=body["recipient_id"],
                amount=Decimal(str(body["amount"])),
                payment_date=payment_date,
                payment_method=body.get("payment_method"),
                notes=body.get("notes"),
                reference_id=body.get("reference_id"),
                created_by=admin_code[:8] + "…"
            )

        return jsonify({
            "id": str(payment.id),
            "message": "Payment recorded successfully"
        }), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.error(f"Error recording payment: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.put("/<public_code>/payments/<payment_id>")
def update_payment_transaction(public_code: str, payment_id: str):
    """
    Update an existing payment transaction (admin only).
    
    Body expects:
    {
      "payer_id": "uuid",
      "recipient_id": "uuid", 
      "amount": 125.50,
      "payment_date": "2025-09-03T10:30:00Z",  // optional
      "payment_method": "Venmo",               // optional
      "notes": "Updated settlement",           // optional
      "reference_id": "venmo_12345"            // optional
    }
    Header: X-Admin-Code: <admin_code>
    """
    try:
        admin_code = request.headers.get("X-Admin-Code")
        if not admin_code:
            return jsonify({"error": "X-Admin-Code header required"}), 401

        # Get game and validate admin access
        from services.session_ingestion_service import _require_admin_for_game
        with SessionLocal() as db:
            game = _require_admin_for_game(db, public_code, admin_code)
            
            # Find the payment transaction
            payment = db.query(PaymentTransaction).filter(
                PaymentTransaction.id == payment_id,
                PaymentTransaction.game_id == str(game.id)
            ).first()
            
            if not payment:
                return jsonify({"error": "Payment transaction not found"}), 404

            body = request.get_json(force=True)
            if not body:
                return jsonify({"error": "JSON body required"}), 400

            # Validate required fields
            required_fields = ["payer_id", "recipient_id", "amount"]
            if not all(field in body for field in required_fields):
                return jsonify({"error": f"Required fields: {required_fields}"}), 400

            # Parse payment date
            payment_date = payment.payment_date  # Keep existing if not provided
            if "payment_date" in body and body["payment_date"]:
                try:
                    payment_date = datetime.fromisoformat(body["payment_date"].replace('Z', '+00:00'))
                except ValueError:
                    return jsonify({"error": "Invalid payment_date format"}), 400

            # Update payment fields
            payment.payer_id = body["payer_id"]
            payment.recipient_id = body["recipient_id"]
            payment.amount_cents = int(float(body["amount"]) * 100)
            payment.payment_method = body.get("payment_method")
            payment.payment_date = payment_date
            payment.notes = body.get("notes")
            payment.reference_id = body.get("reference_id")
            
            # Set audit context
            with audit_context(
                operation_type="PAYMENT_UPDATE",
                game_id=str(game.id),
                actor_kind="admin_code",
                actor_id=admin_code[:8] + "…"
            ):
                db.commit()
                
                # Update payment balances
                payment_service._update_payment_balances(db, str(game.id), [body["payer_id"], body["recipient_id"]])

        return jsonify({
            "id": str(payment.id),
            "message": "Payment updated successfully"
        }), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.error(f"Error updating payment: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.delete("/<public_code>/payments/<payment_id>")
def delete_payment_transaction(public_code: str, payment_id: str):
    """
    Delete a payment transaction (admin only).
    
    Header: X-Admin-Code: <admin_code>
    """
    try:
        admin_code = request.headers.get("X-Admin-Code")
        if not admin_code:
            return jsonify({"error": "X-Admin-Code header required"}), 401

        # Get game and validate admin access
        from services.session_ingestion_service import _require_admin_for_game
        with SessionLocal() as db:
            game = _require_admin_for_game(db, public_code, admin_code)
            
            # Find the payment transaction
            payment = db.query(PaymentTransaction).filter(
                PaymentTransaction.id == payment_id,
                PaymentTransaction.game_id == str(game.id)
            ).first()
            
            if not payment:
                return jsonify({"error": "Payment transaction not found"}), 404

            # Store player IDs for balance update
            payer_id = str(payment.payer_id)
            recipient_id = str(payment.recipient_id)
            
            # Set audit context
            with audit_context(
                operation_type="PAYMENT_DELETE",
                game_id=str(game.id),
                actor_kind="admin_code",
                actor_id=admin_code[:8] + "…"
            ):
                db.delete(payment)
                db.commit()
                
                # Update payment balances
                payment_service._update_payment_balances(db, str(game.id), [payer_id, recipient_id])

        return jsonify({"message": "Payment deleted successfully"}), 200

    except Exception as e:
        logging.error(f"Error deleting payment: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.put("/<public_code>/sessions/<session_id>/players/<player_id>")
def update_session_player_values(public_code: str, session_id: str, player_id: str):
    """
    Update a player's buy-in, cash-out, and in-game values for a specific session.
    Body expects:
    {
      "buy_in_sum": 2000,  // in cents
      "cash_out_sum": 1500,  // in cents
      "in_game": 500  // in cents
    }
    Header: X-Admin-Code: <admin_code>
    """
    try:
        admin_code = request.headers.get("X-Admin-Code")
        if not admin_code:
            return jsonify({"error": "X-Admin-Code header required"}), 401

        # Verify the game exists and the admin code is valid
        with SessionLocal() as db:
            game = db.query(Game).filter_by(public_code=public_code).first()
            if not game:
                return jsonify({"error": "Game not found"}), 404
                
            if game.admin_code != admin_code:
                return jsonify({"error": "Invalid admin code"}), 403

            # Verify the session exists and belongs to this game
            session = db.query(SessionModel).filter_by(
                id=session_id,
                game_id=game.id
            ).first()
            if not session:
                return jsonify({"error": "Session not found"}), 404

            # Verify the player summary exists
            player_summary = db.query(SessionPlayerSummary).filter_by(
                session_id=session_id,
                player_id=player_id
            ).first()
            if not player_summary:
                return jsonify({"error": "Player summary not found"}), 404

            body = request.get_json(force=True)
            if not body:
                return jsonify({"error": "Request body is required"}), 400

            # Validate required fields
            required_fields = ["buy_in_sum", "cash_out_sum", "in_game"]
            for field in required_fields:
                if field not in body:
                    return jsonify({"error": f"{field} is required"}), 400
                if not isinstance(body[field], (int, float)):
                    return jsonify({"error": f"{field} must be a number"}), 400

            # Store old values for audit
            old_values = {
                "buy_in_sum": player_summary.buy_in_sum,
                "cash_out_sum": player_summary.cash_out_sum,
                "in_game": player_summary.in_game,
                "net": player_summary.net
            }

            # Update the values
            player_summary.buy_in_sum = int(body["buy_in_sum"])
            player_summary.cash_out_sum = int(body["cash_out_sum"])
            player_summary.in_game = int(body["in_game"])
            
            # Recalculate net
            player_summary.net = player_summary.cash_out_sum + player_summary.in_game - player_summary.buy_in_sum

            new_values = {
                "buy_in_sum": player_summary.buy_in_sum,
                "cash_out_sum": player_summary.cash_out_sum,
                "in_game": player_summary.in_game,
                "net": player_summary.net
            }

            # Set audit context and commit
            with audit_context(
                operation_type="SESSION_PLAYER_UPDATE",
                game_id=str(game.id),
                actor_kind="admin_code",
                actor_id=admin_code[:8] + "…"
            ):
                db.commit()

        return jsonify({
            "message": "Player session values updated successfully",
            "player_id": player_id,
            "session_id": session_id,
            "old_values": old_values,
            "new_values": new_values
        }), 200

    except Exception as e:
        logging.error(f"Error updating session player values: {e}")
        return jsonify({"error": str(e)}), 500


@game_bp.post("/<public_code>/players/<source_player_id>/merge-into/<target_player_id>")
def merge_players(public_code: str, source_player_id: str, target_player_id: str):
    """
    Merge source player into target player by transferring all session summaries,
    payments, and relationships, then delete the source player.
    """
    admin_code = request.headers.get('X-Admin-Code')
    if not admin_code:
        return jsonify({"error": "Admin code required"}), 401

    with SessionLocal() as db:
        try:
            # Verify admin access
            game = db.query(Game).filter(Game.public_code == public_code).first()
            if not game or game.admin_code != admin_code:
                return jsonify({"error": "Game not found or invalid admin code"}), 404

            # Get both players
            source_player = db.query(Player).filter(Player.id == source_player_id).first()
            target_player = db.query(Player).filter(Player.id == target_player_id).first()
            
            if not source_player or not target_player:
                return jsonify({"error": "One or both players not found"}), 404

            if source_player_id == target_player_id:
                return jsonify({"error": "Cannot merge player into themselves"}), 400

            # Store info for audit
            merge_info = {
                "source_player": {
                    "id": str(source_player.id),
                    "display_name": source_player.display_name,
                    "external_id": source_player.external_id,
                    "is_verified": source_player.is_verified
                },
                "target_player": {
                    "id": str(target_player.id),
                    "display_name": target_player.display_name,
                    "external_id": target_player.external_id,
                    "is_verified": target_player.is_verified
                }
            }

            # Transfer session summaries from source to target
            summaries_to_transfer = db.query(SessionPlayerSummary).filter(
                SessionPlayerSummary.player_id == source_player_id
            ).all()

            transferred_summaries = 0
            merged_summaries = 0
            
            for summary in summaries_to_transfer:
                # Check if target player already has a summary for this session
                existing_summary = db.query(SessionPlayerSummary).filter(
                    SessionPlayerSummary.session_id == summary.session_id,
                    SessionPlayerSummary.player_id == target_player_id
                ).first()

                if existing_summary:
                    # Merge the values (sum them up)
                    existing_summary.buy_in_sum += summary.buy_in_sum
                    existing_summary.cash_out_sum += summary.cash_out_sum
                    existing_summary.in_game += summary.in_game
                    existing_summary.net += summary.net
                    # Merge names arrays, removing duplicates
                    all_names = list(set(existing_summary.names + summary.names))
                    existing_summary.names = all_names
                    # Delete the duplicate summary
                    db.delete(summary)
                    merged_summaries += 1
                else:
                    # Transfer the summary to target player
                    summary.player_id = target_player_id
                    transferred_summaries += 1

            # Transfer payment transactions
            # Update payer_id references
            payer_transactions = db.query(PaymentTransaction).filter(
                PaymentTransaction.payer_id == source_player_id
            ).all()
            
            recipient_transactions = db.query(PaymentTransaction).filter(
                PaymentTransaction.recipient_id == source_player_id
            ).all()

            for transaction in payer_transactions:
                transaction.payer_id = target_player_id

            for transaction in recipient_transactions:
                transaction.recipient_id = target_player_id

            # Transfer payment balances (or merge if target already has balance for this game)
            source_balances = db.query(PaymentBalance).filter(
                PaymentBalance.player_id == source_player_id
            ).all()

            merged_balances = 0
            transferred_balances = 0

            for source_balance in source_balances:
                existing_balance = db.query(PaymentBalance).filter(
                    PaymentBalance.game_id == source_balance.game_id,
                    PaymentBalance.player_id == target_player_id
                ).first()

                if existing_balance:
                    # Merge the balances
                    existing_balance.total_paid += source_balance.total_paid
                    existing_balance.total_received += source_balance.total_received
                    existing_balance.poker_net_winnings += source_balance.poker_net_winnings
                    existing_balance.payment_balance += source_balance.payment_balance
                    existing_balance.last_updated = func.now()
                    # Delete the source balance
                    db.delete(source_balance)
                    merged_balances += 1
                else:
                    # Transfer the balance to target player
                    source_balance.player_id = target_player_id
                    transferred_balances += 1

            # Update game player relationships
            source_game_links = db.query(GamePlayer).filter(GamePlayer.player_id == source_player_id).all()
            transferred_links = 0
            
            for link in source_game_links:
                existing_link = db.query(GamePlayer).filter(
                    GamePlayer.game_id == link.game_id,
                    GamePlayer.player_id == target_player_id
                ).first()

                if existing_link:
                    # Target player already linked to this game, just delete source link
                    db.delete(link)
                else:
                    # Transfer the link to target player
                    link.player_id = target_player_id
                    transferred_links += 1

            # Update target player with better info if source has data that target lacks
            updated_fields = []
            
            # Skip external_id transfer to avoid constraint violations
            # The external_id uniqueness constraint causes issues when merging
            # Just keep the target player's existing external_id (or lack thereof)
            
            # If source is verified but target isn't, make target verified
            if source_player.is_verified and not target_player.is_verified:
                target_player.is_verified = True
                updated_fields.append("is_verified")

            # Create audit log
            with audit_context(operation_type="PLAYER_MERGE"):
                db.add(AuditLog(
                    game_id=game.id,
                    actor_kind="admin_code",
                    actor_id=admin_code[:8] + "…",
                    action="MERGE_PLAYERS",
                    target_table="players",
                    target_id=str(target_player_id),
                    before=merge_info,
                    after={
                        "transferred_summaries": transferred_summaries,
                        "merged_summaries": merged_summaries,
                        "transferred_balances": transferred_balances,
                        "merged_balances": merged_balances,
                        "transferred_links": transferred_links,
                        "updated_fields": updated_fields,
                        "target_player_final": {
                            "id": str(target_player.id),
                            "display_name": target_player.display_name,
                            "external_id": target_player.external_id,
                            "is_verified": target_player.is_verified
                        }
                    }
                ))

            # Finally, delete the source player
            db.delete(source_player)

            db.commit()

            return jsonify({
                "message": f"Successfully merged '{source_player.display_name}' into '{target_player.display_name}'",
                "source_player": merge_info["source_player"],
                "target_player": {
                    "id": str(target_player.id),
                    "display_name": target_player.display_name,
                    "external_id": target_player.external_id,
                    "is_verified": target_player.is_verified
                },
                "transfer_summary": {
                    "transferred_summaries": transferred_summaries,
                    "merged_summaries": merged_summaries,
                    "total_summaries": transferred_summaries + merged_summaries,
                    "transferred_payment_transactions": len(payer_transactions) + len(recipient_transactions),
                    "transferred_balances": transferred_balances,
                    "merged_balances": merged_balances,
                    "transferred_game_links": transferred_links,
                    "updated_target_fields": updated_fields
                }
            }), 200

        except Exception as e:
            db.rollback()
            logging.error(f"Error merging players: {e}")
            return jsonify({"error": str(e)}), 500


@game_bp.post("/<public_code>/players/check-verification-status")
def check_verification_status(public_code: str):
    """
    Check verification status for a list of external_ids.
    Expects: {"external_ids": ["id1", "id2", "id3"]}
    Returns: {"id1": {"is_verified": true, "display_name": "John"}, ...}
    """
    try:
        data = request.get_json()
        external_ids = data.get('external_ids', [])
        
        if not external_ids:
            return jsonify({}), 200

        with SessionLocal() as db:
            # Get game to ensure it exists
            game = db.query(Game).filter(Game.public_code == public_code).first()
            if not game:
                return jsonify({"error": "Game not found"}), 404

            # Find players with these external_ids that are linked to this game
            players = db.query(Player).join(
                GamePlayer, Player.id == GamePlayer.player_id
            ).filter(
                GamePlayer.game_id == game.id,
                Player.external_id.in_(external_ids)
            ).all()

            # Build response map
            result = {}
            for external_id in external_ids:
                player = next((p for p in players if p.external_id == external_id), None)
                if player:
                    result[external_id] = {
                        "is_verified": player.is_verified,
                        "display_name": player.display_name,
                        "player_id": str(player.id)
                    }
                else:
                    result[external_id] = {
                        "is_verified": False,
                        "display_name": None,
                        "player_id": None
                    }

            return jsonify(result), 200

    except Exception as e:
        logging.error(f"Error checking verification status: {e}")
        return jsonify({"error": str(e)}), 500


@game_bp.put("/<public_code>/ledger/manual/new")
def add_manual_ledger_row(public_code: str):
    """
    Add a new manual row to the ledger.
    Creates a new player and session summary entry.
    """
    admin_code = request.headers.get('X-Admin-Code')
    if not admin_code:
        return jsonify({"error": "Admin code required"}), 401

    data = request.get_json()
    session_external_id = data.get('session_external_id')
    player_name = data.get('player_name')
    buy_in_sum = data.get('buy_in_sum', 0)
    cash_out_sum = data.get('cash_out_sum', 0)
    in_game = data.get('in_game', 0)

    if not session_external_id or not player_name:
        return jsonify({"error": "Session ID and player name are required"}), 400

    with SessionLocal() as db:
        try:
            # Verify admin access
            game = db.query(Game).filter(Game.public_code == public_code).first()
            if not game or game.admin_code != admin_code:
                return jsonify({"error": "Game not found or invalid admin code"}), 404

            # Find or create session
            session = db.query(SessionModel).filter(
                SessionModel.game_id == game.id,
                SessionModel.external_id == session_external_id
            ).first()

            if not session:
                # Create new session
                session = SessionModel(
                    game_id=game.id,
                    external_id=session_external_id,
                    session_type='manual',
                    session_name=f'Manual Entry - {session_external_id}',
                    game_number=db.query(func.max(SessionModel.game_number)).filter(
                        SessionModel.game_id == game.id
                    ).scalar() or 0 + 1
                )
                db.add(session)
                db.flush()

            # Find or create player
            player = db.query(Player).join(GamePlayer).filter(
                GamePlayer.game_id == game.id,
                func.lower(Player.display_name) == player_name.lower()
            ).first()

            if not player:
                # Create new player
                player = Player(display_name=player_name)
                db.add(player)
                db.flush()
                
                # Link player to game
                db.add(GamePlayer(game_id=game.id, player_id=player.id))

            # Check if player already has a summary for this session
            existing_summary = db.query(SessionPlayerSummary).filter(
                SessionPlayerSummary.session_id == session.id,
                SessionPlayerSummary.player_id == player.id
            ).first()

            if existing_summary:
                return jsonify({"error": "Player already has an entry for this session"}), 400

            # Calculate net
            net = cash_out_sum + in_game - buy_in_sum

            # Create session player summary
            summary = SessionPlayerSummary(
                session_id=session.id,
                player_id=player.id,
                buy_in_sum=buy_in_sum,
                cash_out_sum=cash_out_sum,
                in_game=in_game,
                net=net,
                names=[player_name]
            )
            db.add(summary)

            # Create audit log
            with audit_context(operation_type="MANUAL_ROW_ADD"):
                db.add(AuditLog(
                    game_id=game.id,
                    session_id=session.id,
                    actor_kind="admin_code",
                    actor_id=admin_code[:8] + "…",
                    action="CREATE",
                    target_table="session_player_summaries",
                    target_id=str(summary.session_id) + ":" + str(summary.player_id),
                    before=None,
                    after={
                        "session_external_id": session_external_id,
                        "player_name": player_name,
                        "buy_in_sum": buy_in_sum,
                        "cash_out_sum": cash_out_sum,
                        "in_game": in_game,
                        "net": net
                    }
                ))

            db.commit()

            return jsonify({
                "message": "Row added successfully",
                "session_id": str(session.id),
                "player_id": str(player.id),
                "player_name": player_name,
                "session_external_id": session_external_id,
                "net": net
            }), 200

        except Exception as e:
            db.rollback()
            logging.error(f"Error adding manual row: {e}")
            return jsonify({"error": str(e)}), 500