from sqlalchemy import text
from db.database import SessionLocal
from flask import Blueprint, request, jsonify
import logging
from services.transaction_service import get_game_transactions
from services.sheets_service import upload_game_to_sheets
from services.dual_write_service import upload_game_dual_write
from services.game_summary_service import get_player_summaries
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
    get_player_details
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

        result = upload_game_dual_write(
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
        result = upload_game_dual_write(
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
        from services.dual_write_service import _require_admin_for_game
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
        from services.dual_write_service import _require_admin_for_game
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
        from services.dual_write_service import _require_admin_for_game
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
        from services.dual_write_service import _require_admin_for_game
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
        from services.dual_write_service import _require_admin_for_game
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
        from services.dual_write_service import _require_admin_for_game
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