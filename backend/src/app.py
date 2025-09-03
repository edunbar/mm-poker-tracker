from flask import Flask
from flask_cors import CORS
from routes.game import game_bp
from services.audit_middleware import setup_request_audit_context, teardown_request_audit_context
import services.audit_middleware  # Initialize the event listeners
import os

def create_app():
    app = Flask(__name__)

    # CORS for local FE
    CORS(app, resources={r"/*": {"origins": ["http://localhost:3000"]}})

    # Register routes
    app.register_blueprint(game_bp, url_prefix="/api/games")

    # Set up audit middleware
    app.before_request(setup_request_audit_context)
    app.teardown_appcontext(teardown_request_audit_context)

    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)