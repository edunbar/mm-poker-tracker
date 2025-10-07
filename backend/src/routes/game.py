from sqlalchemy import text
from db.database import SessionLocal
from flask import Blueprint, request, jsonify
import logging
from services.transaction_service import get_game_transactions
from services.session_ingestion_service import ingest_session
from services.game_summary_service_v2 import get_player_summaries, get_player_analytics, get_session_extremes
from services.ledger_service_v2 import (
    get_all_session_summaries,
    get_session_summary,
    update_session_summary,
    delete_session_summary,
    delete_entire_session
)
# player_verification_service imports removed - use player merge instead
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
from services.live_game_service_v2 import (
    validate_live_game_data,
    create_live_game_session_data,
    validate_session_balance
)
from services.game_creation_service_v2 import (
    create_game,
    validate_game_title
)
from services.payment_service_v2 import PaymentService
from services.hand_log_service import HandLogService
from services.hand_analytics_service import get_hand_analytics
from services.poker_statistics_service import PokerStatisticsProcessor
from services.game_statistics_config_service import GameStatisticsConfigService
from decimal import Decimal
from datetime import timezone, datetime
from sqlalchemy import func
from db.models import Game, Player, PaymentTransaction, PaymentBalance, Session as SessionModel, SessionPlayerSummary, GamePlayer, AuditLog
from werkzeug.datastructures import FileStorage

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
        try:
            body = request.get_json() or {}
        except Exception:
            # Handle invalid JSON gracefully
            return jsonify({"error": "Invalid JSON in request body"}), 400

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

        ledger_csv_content = body.get("ledger_csv_content")

        result = ingest_session(
            public_code=public_code,
            admin_code=admin_code,
            session_id=session_id,
            game_data=game_data,
            date_iso=date_iso,
            manual_game_number=game_number,
            ledger_csv_content=ledger_csv_content,
        )
        return jsonify(result), 200

    except PermissionError as e:
        logging.error(f"Forbidden: {e}")
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        error_msg = str(e)
        if "Game not found" in error_msg:
            logging.error(f"Not found: {e}")
            return jsonify({"error": error_msg}), 404
        else:
            logging.error(f"Bad request: {e}")
            return jsonify({"error": error_msg}), 400
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
        logging.error(f"Forbidden: {e}")
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        logging.error(f"Bad request: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.exception("Unexpected error in /upload_live")
        return jsonify({"error": "Internal server error"}), 500

@game_bp.get("/<public_code>/summary")
def players_summary(public_code: str):
    try:
        result = get_player_summaries(public_code)
        title = result.get("title")
        rows = result.get("rows", [])

        # Add service version info for debugging
        from services import get_service_info
        service_info = get_service_info()

        return jsonify({
            "game": public_code,
            "title": title,
            "rows": rows,
            "_service_info": {
                "game_summary_service_version": service_info.get("game_summary_service", "unknown"),
                "use_domain_services": service_info.get("use_domain_services", False),
                "direct_import": "game_summary_service_v2"
            }
        })
    except ValueError as e:
        logging.error(f"Game not found: {e}")
        return jsonify({"error": "Game not found"}), 404
    except Exception as e:
        logging.exception("Error fetching player summaries")
        return jsonify({"error": "Internal server error"}), 500

@game_bp.get("/<public_code>/analytics")
def players_analytics(public_code: str):
    """
    Get advanced player analytics including streak calculations.
    """
    try:
        result = get_player_analytics(public_code)
        return jsonify(result)
    except ValueError as e:
        logging.error(f"Game not found: {e}")
        return jsonify({"error": "Game not found"}), 404
    except Exception as e:
        logging.error(f"Error fetching player analytics: {e}")
        return jsonify({"error": "Failed to fetch analytics"}), 500

@game_bp.get("/<public_code>/extremes")
@game_bp.get("/<public_code>/session-extremes")  # Alias for frontend compatibility
def players_session_extremes(public_code: str):
    """
    Get the actual best and worst single session performances.
    """
    try:
        result = get_session_extremes(public_code)
        return jsonify(result)
    except ValueError as e:
        logging.error(f"Game not found: {e}")
        return jsonify({"error": "Game not found"}), 404
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

        # Add service version info for debugging
        from services import get_service_info
        service_info = get_service_info()
        result["_service_info"] = {
            "ledger_service_version": service_info.get("ledger_service", "unknown"),
            "use_domain_services": service_info.get("use_domain_services", False)
        }

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

    except PermissionError as e:
        logging.error(f"Forbidden: {e}")
        return jsonify({"error": str(e)}), 403
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

@game_bp.put("/<public_code>/sessions/<session_id>/date")
def update_session_date(public_code: str, session_id: str):
    """
    Update the session started_at date.
    Header: X-Admin-Code: <admin_code>
    Body: { "started_at": "2025-01-15" }
    """
    try:
        admin_code = request.headers.get("X-Admin-Code")
        if not admin_code:
            return jsonify({"error": "X-Admin-Code header required"}), 401

        body = request.get_json()
        started_at_str = body.get("started_at")

        if not started_at_str:
            return jsonify({"error": "started_at is required"}), 400

        # Validate admin code for this game
        from services.session_ingestion_service import _require_admin_for_game
        with SessionLocal() as db:
            game = _require_admin_for_game(db, public_code, admin_code)

            # Find the session (session_id is external_id from URL)
            session = db.query(SessionModel).filter(
                SessionModel.external_id == session_id,
                SessionModel.game_id == game.id
            ).first()

            if not session:
                return jsonify({"error": "Session not found"}), 404

            # Parse and update the date
            from datetime import datetime
            try:
                new_date = datetime.fromisoformat(started_at_str.replace('Z', '+00:00'))
                old_date = session.started_at
                session.started_at = new_date

                # Create audit log entry
                audit_entry = AuditLog(
                    game_id=str(game.id),
                    session_id=str(session.id),
                    actor_kind="admin_code",
                    actor_id=admin_code[:8] + "…",
                    action="UPDATE_SESSION_DATE",
                    target_table="sessions",
                    target_id=str(session.id),
                    before={"started_at": old_date.isoformat() if old_date else None},
                    after={"started_at": new_date.isoformat()}
                )
                db.add(audit_entry)

                db.commit()

                return jsonify({
                    "message": "Session date updated successfully",
                    "session_id": str(session.id),
                    "old_date": old_date.isoformat() if old_date else None,
                    "new_date": new_date.isoformat()
                }), 200

            except ValueError as e:
                return jsonify({"error": f"Invalid date format: {str(e)}"}), 400

    except PermissionError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        logging.error(f"Error updating session date: {e}")
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

    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logging.error(f"Error deleting entire session: {e}")
        return jsonify({"error": str(e)}), 500

# Player verification endpoints removed - use player merge functionality instead

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

    Automatically refreshes payment balances to ensure accurate analysis.
    """
    try:
        # Refresh payment balances before analysis to ensure accuracy
        with SessionLocal() as db:
            game = db.query(Game).filter(Game.public_code == public_code).first()
            if game:
                try:
                    # Get all players who have played in this game
                    player_ids = db.query(SessionPlayerSummary.player_id).distinct()\
                        .join(SessionModel, SessionPlayerSummary.session_id == SessionModel.id)\
                        .filter(SessionModel.game_id == game.id)\
                        .all()

                    player_id_list = [str(pid[0]) for pid in player_ids]

                    # Recalculate payment balances using PaymentService
                    payment_service = PaymentService(db)
                    payment_service._update_payment_balances(db, str(game.id), player_id_list)

                    db.commit()

                    logging.info(f"Refreshed payment balances for {len(player_id_list)} players before analysis")
                except Exception as e:
                    logging.warning(f"Failed to refresh payment balances before analysis: {e}")
                    # Continue with analysis even if refresh fails

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

@game_bp.get("/<public_code>/payments")
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
                # Return empty list for invalid games rather than error
                return jsonify([]), 200

            payment_service = PaymentService(db)
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
                    "realized_earnings": float(player_summary.realized_earnings),
                    "days_since_last_payment": player_summary.days_since_last_payment
                })

            return jsonify(result), 200
            
    except Exception as e:
        logging.error(f"Error getting payment summary: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.get("/<public_code>/payments/summary")
def get_payment_summary_wrapped(public_code: str):
    """
    Get payment summary for all players in the game with wrapped response.
    Returns current balances and payment status in {players: [...]} format.
    """
    try:
        # Get game by public code
        with SessionLocal() as db:
            game = db.query(Game).filter(Game.public_code == public_code).first()
            if not game:
                # Return empty list for invalid games rather than error
                return jsonify({"players": []}), 200

            payment_service = PaymentService(db)
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
                    "realized_earnings": float(player_summary.realized_earnings),
                    "days_since_last_payment": player_summary.days_since_last_payment
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

            payment_service = PaymentService(db)
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

            payment_service = PaymentService(db)
            history = payment_service.get_payment_history(
                str(game.id),
                limit=limit,
                offset=offset
            )

            return jsonify({"transactions": history}), 200
            
    except Exception as e:
        logging.error(f"Error getting payment history: {e}")
        return jsonify({"error": str(e)}), 500

@game_bp.post("/<public_code>/payments")
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
            payment_service = PaymentService(db)
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

            db.commit()
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

                # Note: v2 payment service handles balance updates automatically

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

            # Verify payment exists and belongs to this game
            payment = db.query(PaymentTransaction).filter(
                PaymentTransaction.id == payment_id,
                PaymentTransaction.game_id == str(game.id)
            ).first()

            if not payment:
                return jsonify({"error": "Payment transaction not found"}), 404

            # Use v2 service to delete payment (handles balance updates automatically)
            payment_service = PaymentService(db)
            with audit_context(
                operation_type="PAYMENT_DELETE",
                game_id=str(game.id),
                actor_kind="admin_code",
                actor_id=admin_code[:8] + "…"
            ):
                deleted = payment_service.delete_payment(payment_id)
                if not deleted:
                    return jsonify({"error": "Payment not found"}), 404

            db.commit()
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


# check-verification-status endpoint removed - use player merge functionality instead


@game_bp.post("/<public_code>/payments/cleanup-orphaned")
def cleanup_orphaned_payment_balances(public_code: str):
    """
    Clean up orphaned payment balances for players with no session activity.
    Admin only endpoint.
    Header: X-Admin-Code: <admin_code>
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

            # Find orphaned balances for this game
            balances = db.query(PaymentBalance).filter(
                PaymentBalance.game_id == game.id
            ).all()

            deleted_count = 0
            deleted_players = []

            for balance in balances:
                # Check if player has any session activity in this game
                has_activity = db.query(SessionPlayerSummary).join(
                    SessionModel, SessionPlayerSummary.session_id == SessionModel.id
                ).filter(
                    SessionModel.game_id == game.id,
                    SessionPlayerSummary.player_id == balance.player_id
                ).count() > 0

                if not has_activity:
                    player = db.query(Player).filter(Player.id == balance.player_id).first()
                    deleted_players.append({
                        "player_id": str(balance.player_id),
                        "player_name": player.display_name if player else "Unknown"
                    })
                    db.delete(balance)
                    deleted_count += 1

            if deleted_count > 0:
                db.commit()

            return jsonify({
                "message": f"Cleaned up {deleted_count} orphaned payment balance(s)",
                "deleted_count": deleted_count,
                "deleted_players": deleted_players
            }), 200

        except Exception as e:
            db.rollback()
            logging.error(f"Error cleaning up orphaned balances: {e}")
            return jsonify({"error": str(e)}), 500


@game_bp.post("/<public_code>/payments/recalculate-balances")
def recalculate_payment_balances(public_code: str):
    """
    Recalculate all payment balances for a game.
    Useful after data corrections or migrations.
    Admin only endpoint.
    Header: X-Admin-Code: <admin_code>
    """
    admin_code = request.headers.get('X-Admin-Code')
    if not admin_code:
        return jsonify({"error": "Admin code required"}), 401

    with SessionLocal() as db:
        try:
            game = db.query(Game).filter(Game.public_code == public_code).first()
            if not game or game.admin_code != admin_code:
                return jsonify({"error": "Game not found or invalid admin code"}), 404

            # Get all players who have played in this game
            player_ids = db.query(SessionPlayerSummary.player_id).distinct()\
                .join(SessionModel, SessionPlayerSummary.session_id == SessionModel.id)\
                .filter(SessionModel.game_id == game.id)\
                .all()

            player_id_list = [str(pid[0]) for pid in player_ids]

            # Recalculate balances for all players using PaymentService
            payment_service = PaymentService(db)
            payment_service._update_payment_balances(db, str(game.id), player_id_list)

            db.commit()

            return jsonify({
                "message": f"Successfully recalculated payment balances for {len(player_id_list)} player(s)",
                "players_updated": len(player_id_list)
            }), 200

        except Exception as e:
            db.rollback()
            logging.error(f"Error recalculating payment balances: {e}")
            return jsonify({"error": str(e)}), 500


# ==========================================================
# Alert System Endpoints
# ==========================================================

@game_bp.get("/<public_code>/alerts/rules")
def get_alert_rules(public_code: str):
    """
    Get alert rules for a game (admin only).

    Returns all alert rules configured for the game.
    Header: X-Admin-Code: <admin_code>
    """
    try:
        admin_code = request.headers.get("X-Admin-Code")
        if not admin_code:
            return jsonify({"error": "X-Admin-Code header required"}), 401

        from services.session_ingestion_service import _require_admin_for_game
        with SessionLocal() as db:
            game = _require_admin_for_game(db, public_code, admin_code)

            from services.alert_service import AlertService
            alert_service = AlertService(db)
            rules = alert_service.get_alert_rules(str(game.id))

            return jsonify({"rules": [r.to_dict() for r in rules]}), 200

    except PermissionError as e:
        logging.error(f"Permission error getting alert rules: {e}")
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        logging.error(f"Value error getting alert rules: {e}")
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logging.error(f"Error getting alert rules: {e}")
        return jsonify({"error": str(e)}), 500


@game_bp.post("/<public_code>/alerts/rules")
def create_alert_rule(public_code: str):
    """
    Create new alert rule (admin only).

    Body expects:
    {
      "rule_type": "amount_threshold" | "days_overdue",
      "threshold_value": int  // cents for amount_threshold, days for days_overdue
    }
    Header: X-Admin-Code: <admin_code>
    """
    try:
        admin_code = request.headers.get("X-Admin-Code")
        if not admin_code:
            return jsonify({"error": "X-Admin-Code header required"}), 401

        body = request.get_json(force=True)
        if not body:
            return jsonify({"error": "Request body required"}), 400

        rule_type = body.get('rule_type')
        threshold_value = body.get('threshold_value')

        if not rule_type or threshold_value is None:
            return jsonify({"error": "rule_type and threshold_value required"}), 400

        from services.session_ingestion_service import _require_admin_for_game
        with SessionLocal() as db:
            game = _require_admin_for_game(db, public_code, admin_code)

            from services.alert_service import AlertService
            alert_service = AlertService(db)
            rule = alert_service.create_alert_rule(
                str(game.id),
                rule_type,
                int(threshold_value),
                admin_code
            )

            db.commit()

            return jsonify({
                "message": "Alert rule created successfully",
                "rule": rule.to_dict()
            }), 201

    except PermissionError as e:
        logging.error(f"Permission error creating alert rule: {e}")
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        logging.error(f"Value error creating alert rule: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.error(f"Error creating alert rule: {e}")
        return jsonify({"error": str(e)}), 500


@game_bp.put("/<public_code>/alerts/rules/<rule_id>")
def update_alert_rule(public_code: str, rule_id: str):
    """
    Update alert rule threshold and active status (admin only).

    Body expects:
    {
      "threshold_value": int,
      "is_active": bool  // optional, defaults to true
    }
    Header: X-Admin-Code: <admin_code>
    """
    try:
        admin_code = request.headers.get("X-Admin-Code")
        if not admin_code:
            return jsonify({"error": "X-Admin-Code header required"}), 401

        body = request.get_json(force=True)
        if not body:
            return jsonify({"error": "Request body required"}), 400

        threshold_value = body.get('threshold_value')
        is_active = body.get('is_active', True)

        if threshold_value is None:
            return jsonify({"error": "threshold_value required"}), 400

        from services.session_ingestion_service import _require_admin_for_game
        with SessionLocal() as db:
            game = _require_admin_for_game(db, public_code, admin_code)

            from services.alert_service import AlertService
            alert_service = AlertService(db)
            rule = alert_service.update_alert_rule(
                str(game.id),
                rule_id,
                int(threshold_value),
                is_active,
                admin_code
            )

            db.commit()

            return jsonify({
                "message": "Alert rule updated successfully",
                "rule": rule.to_dict()
            }), 200

    except PermissionError as e:
        logging.error(f"Permission error updating alert rule: {e}")
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        logging.error(f"Value error updating alert rule: {e}")
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logging.error(f"Error updating alert rule: {e}")
        return jsonify({"error": str(e)}), 500


@game_bp.delete("/<public_code>/alerts/rules/<rule_id>")
def delete_alert_rule(public_code: str, rule_id: str):
    """
    Delete alert rule (admin only).

    Header: X-Admin-Code: <admin_code>
    """
    try:
        admin_code = request.headers.get("X-Admin-Code")
        if not admin_code:
            return jsonify({"error": "X-Admin-Code header required"}), 401

        from services.session_ingestion_service import _require_admin_for_game
        with SessionLocal() as db:
            game = _require_admin_for_game(db, public_code, admin_code)

            from services.alert_service import AlertService
            alert_service = AlertService(db)
            success = alert_service.delete_alert_rule(str(game.id), rule_id, admin_code)

            if not success:
                return jsonify({"error": "Alert rule not found"}), 404

            db.commit()

            return jsonify({"message": "Alert rule deleted successfully"}), 200

    except PermissionError as e:
        logging.error(f"Permission error deleting alert rule: {e}")
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        logging.error(f"Value error deleting alert rule: {e}")
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logging.error(f"Error deleting alert rule: {e}")
        return jsonify({"error": str(e)}), 500


@game_bp.get("/<public_code>/alerts/status")
def get_alert_status(public_code: str):
    """
    Get computed alert violations for the game (public endpoint).

    Computes violations on-demand from current player balances and active rules.
    Returns players who owe money and violate any active alert rules.
    This endpoint is public since it only exposes existing payment data with highlighting.
    """
    try:
        with SessionLocal() as db:
            # Look up game by public code
            game = db.query(Game).filter_by(public_code=public_code).first()
            if not game:
                return jsonify({"error": "Game not found"}), 404

            from services.alert_service import AlertService
            alert_service = AlertService(db)
            status = alert_service.compute_alert_status(str(game.id))

            # Convert cents to dollars in API response for frontend convenience
            response = status.to_dict()
            for player_alert in response['player_alerts']:
                player_alert['total_amount_owed_dollars'] = player_alert['total_amount_owed'] / 100.0
                for violation in player_alert['violations']:
                    if violation['rule_type'] == 'amount_threshold':
                        violation['current_value_dollars'] = violation['current_value'] / 100.0
                        violation['threshold_value_dollars'] = violation['threshold_value'] / 100.0

            return jsonify(response), 200

    except ValueError as e:
        logging.error(f"Value error getting alert status: {e}")
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logging.error(f"Error computing alert status: {e}")
        return jsonify({"error": str(e)}), 500


@game_bp.get("/<public_code>/sessions/<session_id>/ledger-csv")
def get_session_ledger_csv(public_code: str, session_id: str):
    """
    Get the ledger CSV content for a specific session.
    """
    try:
        with SessionLocal() as db:
            game = db.query(Game).filter(Game.public_code == public_code).first()
            if not game:
                return jsonify({"error": "Game not found"}), 404

            session = db.query(SessionModel).filter(
                SessionModel.id == session_id,
                SessionModel.game_id == game.id
            ).first()

            if not session:
                return jsonify({"error": "Session not found"}), 404

            if not session.ledger_csv_content:
                return jsonify({"error": "No ledger CSV available for this session"}), 404

            return jsonify({
                "session_id": str(session.id),
                "game_number": session.game_number,
                "csv_content": session.ledger_csv_content
            }), 200

    except Exception as e:
        logging.error(f"Error fetching ledger CSV: {e}")
        return jsonify({"error": str(e)}), 500


@game_bp.post("/<public_code>/sessions/<session_id>/fetch-ledger-csv")
def fetch_and_save_ledger_csv(public_code: str, session_id: str):
    """
    Fetch ledger CSV from PokerNow and save it to an existing session.
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

            # Find the session
            session = db.query(SessionModel).filter(
                SessionModel.id == session_id,
                SessionModel.game_id == game.id
            ).first()

            if not session:
                return jsonify({"error": "Session not found"}), 404

            if not session.external_id:
                return jsonify({"error": "Session has no external_id (PokerNow session ID)"}), 400

            # Build PokerNow URL from external_id
            base_url = f"https://www.pokernow.club/games/{session.external_id}"

            # Fetch CSV using existing service
            from services.transaction_service import fetch_ledger_csv
            ledger_result = fetch_ledger_csv(base_url)

            if not ledger_result.get("success"):
                return jsonify({
                    "error": f"Failed to fetch CSV: {ledger_result.get('error', 'Unknown error')}"
                }), 400

            # Save CSV content to session
            session.ledger_csv_content = ledger_result.get("content")

            # Create audit log
            from services.audit_middleware import audit_context
            with audit_context(
                operation_type="LEDGER_CSV_FETCH",
                game_id=str(game.id),
                actor_kind="admin_code",
                actor_id=admin_code[:8] + "…"
            ):
                db.commit()

            return jsonify({
                "message": "Ledger CSV fetched and saved successfully",
                "session_id": str(session.id),
                "game_number": session.game_number,
                "size_bytes": ledger_result.get("size_bytes")
            }), 200

    except PermissionError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        logging.error(f"Error fetching and saving ledger CSV: {e}")
        return jsonify({"error": str(e)}), 500


@game_bp.post("/<public_code>/sessions/<session_id>/upload-hand-log")
def upload_hand_log(public_code: str, session_id: str):
    admin_code = request.headers.get('X-Admin-Code')
    if not admin_code:
        return jsonify({"error": "Admin code required"}), 401

    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.endswith('.csv'):
        return jsonify({"error": "File must be a CSV"}), 400

    with SessionLocal() as db:
        try:
            game = db.query(Game).filter(Game.public_code == public_code).first()
            if not game or game.admin_code != admin_code:
                return jsonify({"error": "Game not found or invalid admin code"}), 404

            # session_id in URL is actually the external_id (PokerNow session ID)
            session = db.query(SessionModel).filter(
                SessionModel.external_id == session_id,
                SessionModel.game_id == game.id
            ).first()

            if not session:
                return jsonify({"error": "Session not found"}), 404

            csv_content = file.read().decode('utf-8')

            player_mappings_json = request.form.get('player_mappings')
            player_mappings = None
            if player_mappings_json:
                import json
                player_mappings = json.loads(player_mappings_json)

            with audit_context(
                operation_type="HAND_LOG_UPLOAD",
                game_id=str(game.id),
                actor_kind="admin_code",
                actor_id=admin_code[:8] + "…"
            ):
                result = HandLogService.import_hand_log(
                    db=db,
                    session_id=str(session.id),  # Pass the database UUID, not external_id
                    csv_content=csv_content,
                    player_mappings=player_mappings
                )

            return jsonify(result), 200 if result['status'] == 'success' else 202

        except ValueError as e:
            db.rollback()
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            db.rollback()
            logging.error(f"Error uploading hand log: {e}")
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


@game_bp.get("/<public_code>/hand-analytics")
def get_session_hand_analytics(public_code: str):
    """
    Get hand analytics for all sessions with hand data.
    """
    try:
        result = get_hand_analytics(public_code)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logging.error(f"Error fetching hand analytics: {e}")
        return jsonify({"error": str(e)}), 500


# ==========================================================
# Poker Statistics Endpoints
# ==========================================================

@game_bp.route('/<public_code>/sessions/<session_id>/statistics', methods=['GET'])
def get_session_statistics(public_code: str, session_id: str):
    """
    Get poker statistics (VPIP, PFR, AF) for all players in a session.

    Returns:
    {
        "players": [
            {
                "playerId": "uuid",
                "playerName": "thomo!",
                "handsPlayed": 245,
                "vpip": 28.5,
                "pfr": 22.0,
                "aggressionFrequency": 65.3,
                "playStyle": "TAG",
                "flopAF": 70.2,
                "turnAF": 60.1,
                "riverAF": 65.8
            }
        ]
    }
    """
    try:
        with SessionLocal() as db:
            # Validate public code
            game = db.query(Game).filter(Game.public_code == public_code.upper()).first()
            if not game:
                return jsonify({"error": "Game not found"}), 404

            # Validate session belongs to game
            session = db.query(SessionModel).filter(
                SessionModel.id == session_id,
                SessionModel.game_id == game.id
            ).first()

            if not session:
                return jsonify({"error": "Session not found"}), 404

            # Get statistics
            processor = PokerStatisticsProcessor(db)
            players = processor.get_session_statistics(session_id)

            return jsonify({
                "session_id": session_id,
                "session_name": session.session_name,
                "game_number": session.game_number,
                "players": players
            }), 200

    except Exception as e:
        logging.error(f"Error fetching session statistics: {e}")
        return jsonify({"error": str(e)}), 500


@game_bp.route('/<public_code>/sessions/<session_id>/statistics/calculate', methods=['POST'])
def calculate_session_statistics(public_code: str, session_id: str):
    """
    Calculate/recalculate poker statistics for a session.
    Requires admin_code for authorization.

    Headers:
    X-Admin-Code: <admin_code>

    Returns:
    {
        "session_id": "uuid",
        "hands_processed": 150,
        "message": "Statistics calculated successfully"
    }
    """
    try:
        # Check admin authorization
        admin_code = request.headers.get('X-Admin-Code')
        if not admin_code:
            return jsonify({"error": "X-Admin-Code header required"}), 401

        with SessionLocal() as db:
            # Validate admin code
            game = db.query(Game).filter(Game.admin_code == admin_code).first()
            if not game:
                return jsonify({"error": "Invalid admin code"}), 401

            # Validate public code matches
            if game.public_code.upper() != public_code.upper():
                return jsonify({"error": "Public code mismatch"}), 400

            # Validate session belongs to game
            session = db.query(SessionModel).filter(
                SessionModel.id == session_id,
                SessionModel.game_id == game.id
            ).first()

            if not session:
                return jsonify({"error": "Session not found"}), 404

            # Process statistics
            processor = PokerStatisticsProcessor(db)
            result = processor.process_session_statistics(session_id)

            # Create audit log
            with audit_context(
                operation_type="CALCULATE_STATISTICS",
                game_id=str(game.id),
                actor_kind="admin_code",
                actor_id=admin_code[:8] + "…"
            ):
                db.commit()

            return jsonify(result), 200

    except Exception as e:
        db.rollback() if 'db' in locals() else None
        logging.error(f"Error calculating session statistics: {e}")
        return jsonify({"error": str(e)}), 500


@game_bp.route('/<public_code>/players/<player_id>/statistics', methods=['GET'])
def get_player_statistics_across_sessions(public_code: str, player_id: str):
    """
    Get player statistics across all sessions in a game.

    Returns:
    {
        "player": {
            "playerId": "uuid",
            "playerName": "thomo!",
            "overall": {
                "totalHands": 850,
                "vpip": 27.2,
                "pfr": 21.5,
                "aggressionFrequency": 66.8,
                "playStyle": "TAG"
            },
            "bySession": [
                {
                    "sessionId": "uuid",
                    "gameNumber": 5,
                    "handsPlayed": 245,
                    "vpip": 28.5,
                    "pfr": 22.0,
                    "aggressionFrequency": 65.3,
                    "playStyle": "TAG"
                }
            ]
        }
    }
    """
    try:
        with SessionLocal() as db:
            # Validate public code
            game = db.query(Game).filter(Game.public_code == public_code.upper()).first()
            if not game:
                return jsonify({"error": "Game not found"}), 404

            # Validate player exists
            player = db.query(Player).filter(Player.id == player_id).first()
            if not player:
                return jsonify({"error": "Player not found"}), 404

            # Get all session statistics for this player in this game
            from db.models import PlayerStatisticsCache
            stats = (db.query(PlayerStatisticsCache, SessionModel.game_number, SessionModel.session_name)
                    .join(SessionModel, PlayerStatisticsCache.session_id == SessionModel.id)
                    .filter(
                        PlayerStatisticsCache.player_id == player_id,
                        SessionModel.game_id == game.id
                    )
                    .order_by(SessionModel.game_number)
                    .all())

            if not stats:
                return jsonify({"error": "No statistics found for this player in this game"}), 404

            # Calculate overall statistics
            total_hands = sum(stat.hands_dealt for stat, _, _ in stats)
            total_vpip_hands = sum(stat.vpip_hands for stat, _, _ in stats)
            total_pfr_hands = sum(stat.pfr_hands for stat, _, _ in stats)
            total_postflop_aggressive = sum(stat.postflop_aggressive_actions for stat, _, _ in stats)
            total_postflop_actions = sum(stat.postflop_total_actions for stat, _, _ in stats)

            overall_vpip = (total_vpip_hands / total_hands * 100) if total_hands > 0 else 0
            overall_pfr = (total_pfr_hands / total_hands * 100) if total_hands > 0 else 0
            overall_af = (total_postflop_aggressive / total_postflop_actions * 100) if total_postflop_actions > 0 else 0

            # Classify overall play style
            processor = PokerStatisticsProcessor(db)
            overall_style = processor._classify_play_style(overall_vpip, overall_pfr, overall_af)

            # Build by-session data
            by_session = []
            for stat, game_number, session_name in stats:
                by_session.append({
                    "sessionId": str(stat.session_id),
                    "gameNumber": game_number,
                    "sessionName": session_name,
                    "handsPlayed": stat.hands_dealt,
                    "vpip": float(stat.vpip_percentage) if stat.vpip_percentage else 0,
                    "pfr": float(stat.pfr_percentage) if stat.pfr_percentage else 0,
                    "aggressionFrequency": float(stat.aggression_frequency) if stat.aggression_frequency else 0,
                    "playStyle": stat.play_style or 'Unknown'
                })

            return jsonify({
                "player": {
                    "playerId": str(player.id),
                    "playerName": player.display_name,
                    "overall": {
                        "totalHands": total_hands,
                        "vpip": round(overall_vpip, 2),
                        "pfr": round(overall_pfr, 2),
                        "aggressionFrequency": round(overall_af, 2),
                        "playStyle": overall_style or 'Unknown'
                    },
                    "bySession": by_session
                }
            }), 200

    except Exception as e:
        logging.error(f"Error fetching player statistics: {e}")
        return jsonify({"error": str(e)}), 500


@game_bp.route('/<public_code>/statistics', methods=['GET'])
def get_game_statistics(public_code: str):
    """
    Get aggregated poker statistics for all players across all sessions in a game.
    """
    db = SessionLocal()

    try:
        # Get game by public code
        game = db.execute(
            text("SELECT id FROM games WHERE public_code = :public_code"),
            {"public_code": public_code}
        ).fetchone()

        if not game:
            return jsonify({"error": "Game not found"}), 404

        game_id = game[0]

        # Get all sessions with poker statistics for this game
        from db.models import PlayerStatisticsCache, Player, Session

        # Query to get aggregated statistics across all sessions
        stats_query = (
            db.query(
                PlayerStatisticsCache.player_id,
                Player.display_name,
                func.sum(PlayerStatisticsCache.hands_dealt).label('total_hands'),
                func.sum(PlayerStatisticsCache.vpip_hands).label('total_vpip'),
                func.sum(PlayerStatisticsCache.pfr_hands).label('total_pfr'),
                func.sum(PlayerStatisticsCache.postflop_aggressive_actions).label('total_aggressive'),
                func.sum(PlayerStatisticsCache.postflop_passive_actions).label('total_passive'),
                # For street-specific AF, we'll calculate weighted averages from stored percentages
                func.avg(PlayerStatisticsCache.flop_af).label('avg_flop_af'),
                func.avg(PlayerStatisticsCache.turn_af).label('avg_turn_af'),
                func.avg(PlayerStatisticsCache.river_af).label('avg_river_af'),
            )
            .join(Player, PlayerStatisticsCache.player_id == Player.id)
            .join(Session, PlayerStatisticsCache.session_id == Session.id)
            .filter(Session.game_id == game_id)
            .group_by(PlayerStatisticsCache.player_id, Player.display_name)
            .having(func.sum(PlayerStatisticsCache.hands_dealt) > 0)
            .all()
        )

        if not stats_query:
            return jsonify([]), 200

        result = []
        for stat in stats_query:
            # Calculate percentages
            vpip_pct = (stat.total_vpip / stat.total_hands * 100) if stat.total_hands > 0 else 0
            pfr_pct = (stat.total_pfr / stat.total_hands * 100) if stat.total_hands > 0 else 0

            total_postflop = stat.total_aggressive + stat.total_passive
            af_pct = (stat.total_aggressive / total_postflop * 100) if total_postflop > 0 else 0

            flop_af = float(stat.avg_flop_af) if stat.avg_flop_af else 0
            turn_af = float(stat.avg_turn_af) if stat.avg_turn_af else 0
            river_af = float(stat.avg_river_af) if stat.avg_river_af else 0

            # Classify play style
            is_tight = vpip_pct < 25
            is_loose = vpip_pct > 35
            is_aggressive = pfr_pct > 20 and af_pct > 60
            is_passive = pfr_pct < 15 and af_pct < 40

            if is_tight and is_aggressive:
                play_style = 'TAG'
            elif is_loose and is_aggressive:
                play_style = 'LAG'
            elif is_tight and is_passive:
                play_style = 'TP'
            elif is_loose and is_passive:
                play_style = 'LP'
            else:
                play_style = 'Unknown'

            result.append({
                'playerId': str(stat.player_id),
                'playerName': stat.display_name,
                'handsPlayed': stat.total_hands,
                'vpip': round(vpip_pct, 1),
                'pfr': round(pfr_pct, 1),
                'aggressionFrequency': round(af_pct, 1),
                'playStyle': play_style,
                'flopAF': round(flop_af, 1),
                'turnAF': round(turn_af, 1),
                'riverAF': round(river_af, 1),
            })

        # Sort by hands played (descending)
        result.sort(key=lambda x: x['handsPlayed'], reverse=True)

        return jsonify(result)

    except Exception as e:
        logging.error(f"Error fetching game statistics: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@game_bp.route('/<public_code>/statistics-config', methods=['GET'])
def get_game_statistics_config(public_code: str):
    """
    Get current statistics configuration for a game.
    """
    db = SessionLocal()

    try:
        # Get game by public code
        game = db.execute(
            text("SELECT id FROM games WHERE public_code = :public_code"),
            {"public_code": public_code}
        ).fetchone()

        if not game:
            return jsonify({"error": "Game not found"}), 404

        game_id = game[0]
        config_service = GameStatisticsConfigService(db)

        # Get or create configuration
        game_config = config_service.get_or_create_game_config(game_id)
        config_description = config_service.get_config_description(game_config)

        return jsonify({
            "gameId": str(game_id),
            "publicCode": public_code,
            "currentConfig": config_description,
            "availableTypes": config_service.get_available_game_types()
        })

    except Exception as e:
        logging.error(f"Error fetching game statistics config: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@game_bp.route('/<public_code>/statistics-config', methods=['PUT'])
def update_game_statistics_config(public_code: str):
    """
    Update statistics configuration for a game (admin only).
    """
    db = SessionLocal()

    try:
        # Check admin authorization
        admin_code = request.headers.get('X-Admin-Code')
        if not admin_code:
            return jsonify({"error": "Admin code required"}), 401

        # Get game and verify admin code
        game = db.execute(
            text("SELECT id, admin_code FROM games WHERE public_code = :public_code"),
            {"public_code": public_code}
        ).fetchone()

        if not game or game[1] != admin_code:
            return jsonify({"error": "Invalid admin code or game not found"}), 403

        game_id = game[0]
        data = request.get_json()

        if not data or 'configType' not in data:
            return jsonify({"error": "configType is required"}), 400

        config_type = data['configType']
        custom_thresholds = data.get('customThresholds')

        # Update configuration
        config_service = GameStatisticsConfigService(db)
        updated_config = config_service.update_game_config(game_id, config_type, custom_thresholds)
        config_description = config_service.get_config_description(updated_config)

        return jsonify({
            "message": "Statistics configuration updated successfully",
            "gameId": str(game_id),
            "publicCode": public_code,
            "newConfig": config_description
        })

    except ValueError as e:
        return jsonify({"error": f"Invalid configuration: {str(e)}"}), 400
    except Exception as e:
        logging.error(f"Error updating game statistics config: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@game_bp.route('/<public_code>/statistics/adaptive', methods=['GET'])
def get_adaptive_game_statistics(public_code: str):
    """
    Get aggregated poker statistics with adaptive classification based on game configuration.
    """
    db = SessionLocal()

    try:
        # Get game by public code
        game = db.execute(
            text("SELECT id FROM games WHERE public_code = :public_code"),
            {"public_code": public_code}
        ).fetchone()

        if not game:
            return jsonify({"error": "Game not found"}), 404

        game_id = game[0]

        # Get game configuration
        config_service = GameStatisticsConfigService(db)
        game_config = config_service.get_or_create_game_config(game_id)

        # Get all sessions with poker statistics for this game
        from db.models import PlayerStatisticsCache, Player, Session

        # Query to get aggregated statistics across all sessions
        stats_query = (
            db.query(
                PlayerStatisticsCache.player_id,
                Player.display_name,
                func.sum(PlayerStatisticsCache.hands_dealt).label('total_hands'),
                func.sum(PlayerStatisticsCache.vpip_hands).label('total_vpip'),
                func.sum(PlayerStatisticsCache.pfr_hands).label('total_pfr'),
                func.sum(PlayerStatisticsCache.postflop_aggressive_actions).label('total_aggressive'),
                func.sum(PlayerStatisticsCache.postflop_passive_actions).label('total_passive'),
                # For street-specific AF, we'll calculate weighted averages from stored percentages
                func.avg(PlayerStatisticsCache.flop_af).label('avg_flop_af'),
                func.avg(PlayerStatisticsCache.turn_af).label('avg_turn_af'),
                func.avg(PlayerStatisticsCache.river_af).label('avg_river_af'),
            )
            .join(Player, PlayerStatisticsCache.player_id == Player.id)
            .join(Session, PlayerStatisticsCache.session_id == Session.id)
            .filter(Session.game_id == game_id)
            .group_by(PlayerStatisticsCache.player_id, Player.display_name)
            .having(func.sum(PlayerStatisticsCache.hands_dealt) > 0)
            .all()
        )

        if not stats_query:
            return jsonify({
                "config": config_service.get_config_description(game_config),
                "players": []
            }), 200

        result = []
        for stat in stats_query:
            # Calculate percentages
            vpip_pct = (stat.total_vpip / stat.total_hands * 100) if stat.total_hands > 0 else 0
            pfr_pct = (stat.total_pfr / stat.total_hands * 100) if stat.total_hands > 0 else 0

            total_postflop = stat.total_aggressive + stat.total_passive
            af_pct = (stat.total_aggressive / total_postflop * 100) if total_postflop > 0 else 0

            flop_af = float(stat.avg_flop_af) if stat.avg_flop_af else 0
            turn_af = float(stat.avg_turn_af) if stat.avg_turn_af else 0
            river_af = float(stat.avg_river_af) if stat.avg_river_af else 0

            # Get adaptive classification
            classification = config_service.classify_player(vpip_pct, pfr_pct, af_pct, game_config)

            result.append({
                'playerId': str(stat.player_id),
                'playerName': stat.display_name,
                'handsPlayed': stat.total_hands,
                'vpip': round(vpip_pct, 1),
                'pfr': round(pfr_pct, 1),
                'aggressionFrequency': round(af_pct, 1),
                'playStyle': classification.style,
                'styleColor': classification.style_color,
                'styleDescription': classification.description,
                'vpipCategory': classification.vpip_category,
                'pfrCategory': classification.pfr_category,
                'afCategory': classification.af_category,
                'flopAF': round(flop_af, 1),
                'turnAF': round(turn_af, 1),
                'riverAF': round(river_af, 1),
            })

        # Sort by hands played (descending)
        result.sort(key=lambda x: x['handsPlayed'], reverse=True)

        return jsonify({
            "config": config_service.get_config_description(game_config),
            "players": result
        })

    except Exception as e:
        logging.error(f"Error fetching adaptive game statistics: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@game_bp.route('/service-info', methods=['GET'])
def get_service_info_endpoint():
    """
    Get information about which services are currently loaded.
    Useful for debugging service migration status.
    """
    try:
        from services import get_service_info
        info = get_service_info()
        return jsonify(info), 200
    except Exception as e:
        logging.error(f"Error getting service info: {e}")
        return jsonify({"error": str(e)}), 500