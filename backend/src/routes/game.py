from flask import Blueprint, request, jsonify
import logging
from services.transaction_service import get_game_transactions
from services.sheets_service import upload_game_to_sheets
from services.dual_write_service import upload_game_dual_write

game_bp = Blueprint('game', __name__)

logging.basicConfig(level=logging.DEBUG)

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
      "date": "2025-08-11T00:00:00"                # optional; uses 'today' if omitted
    }
    Header: X-Admin-Code: <admin_code>
    """
    try:
        body = request.get_json(force=True)
        public_code = body.get("public_code")
        session_id = body.get("sessionId")
        game_data = body.get("game_data") or {}
        date_iso = body.get("date")

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