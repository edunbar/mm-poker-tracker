from flask import Blueprint, request, jsonify
import logging
from datetime import datetime
from services.email_service import send_bug_report_email, validate_bug_report_data

bug_report_bp = Blueprint('bug_report', __name__)

@bug_report_bp.route('/bug-report', methods=['POST'])
def submit_bug_report():
    """
    Submit a bug report via email

    Request JSON:
    {
        "description": "Bug description",
        "steps_to_reproduce": "Steps to reproduce", (optional)
        "category": "Bug category",  (optional)
        "user_email": "user@example.com", (optional)
        "url": "Current page URL",
        "user_agent": "Browser user agent",
        "game_code": "ABC123" (optional)
    }

    Returns:
        JSON response with success/error status
    """
    try:
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        # Add timestamp
        data['timestamp'] = datetime.utcnow().isoformat() + 'Z'

        # Validate bug report data
        is_valid, errors = validate_bug_report_data(data)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Validation failed',
                'details': errors
            }), 400

        # Send bug report email
        success, message = send_bug_report_email(data)

        if success:
            logging.info(f"Bug report submitted successfully from {request.remote_addr}")
            return jsonify({
                'success': True,
                'message': 'Bug report submitted successfully'
            }), 200
        else:
            logging.error(f"Failed to send bug report: {message}")
            return jsonify({
                'success': False,
                'error': 'Failed to send bug report',
                'details': message
            }), 500

    except Exception as e:
        logging.error(f"Error in bug report submission: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@bug_report_bp.route('/bug-report/categories', methods=['GET'])
def get_bug_categories():
    """
    Get available bug report categories

    Returns:
        JSON list of available categories
    """
    categories = [
        'UI Issue',
        'Functionality',
        'Performance',
        'Data Accuracy',
        'Other'
    ]

    return jsonify({
        'success': True,
        'categories': categories
    }), 200

@bug_report_bp.route('/bug-report/health', methods=['GET'])
def bug_report_health():
    """
    Health check for bug report service

    Returns:
        JSON response indicating if email service is configured
    """
    import os

    # Check if required environment variables are set
    mail_username = os.getenv('MAIL_USERNAME')
    mail_password = os.getenv('MAIL_PASSWORD')
    bug_report_email = os.getenv('BUG_REPORT_EMAIL')

    is_configured = all([mail_username, mail_password, bug_report_email])

    return jsonify({
        'success': True,
        'email_configured': is_configured,
        'message': 'Bug report service ready' if is_configured else 'Email not fully configured'
    }), 200