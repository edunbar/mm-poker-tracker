from flask import Blueprint, request, jsonify
import logging
from services.transaction_service import get_game_transactions
from services.sheets_service import upload_game_to_sheets

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

@game_bp.route('/upload_to_sheets', methods=['POST'])
def upload_to_sheets():
    data = request.json
    try:
        result = upload_game_to_sheets(data)
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error in upload_game_to_sheets: {e}")
        return jsonify({'error': str(e)}), 500