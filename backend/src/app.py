from flask import Flask
from flask_cors import CORS
from extensions import limiter
from routes.game import game_bp
from routes.health import health_bp
from routes.bug_report import bug_report_bp
from routes.rules import rules_bp
from routes.auth import auth_bp
from routes.poker_identity_claim_routes import poker_identity_bp
from routes.live_game_routes import live_game_bp
from routes.live_game_sse import live_game_sse_bp
from services.audit_middleware import setup_request_audit_context, teardown_request_audit_context
import services.audit_middleware  # Initialize the event listeners
import os
import logging
from logging.handlers import RotatingFileHandler

def create_app():
    app = Flask(__name__)

    # Environment-based configuration
    flask_env = os.getenv("FLASK_ENV", "development")


    # Configure CORS based on environment
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    CORS(app, resources={r"/*": {"origins": [origin.strip() for origin in allowed_origins]}})

    # Initialize rate limiter with environment-specific limits
    if flask_env == "production":
        limiter.default_limits = ["2000 per day", "500 per hour"]
    else:
        limiter.default_limits = ["1000 per hour"]

    limiter.init_app(app)

    # Security headers for production
    @app.after_request
    def security_headers(response):
        if flask_env == "production":
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    # Production logging configuration
    if flask_env == "production":
        if not app.debug and not app.testing:
            # File logging
            if not os.path.exists('logs'):
                os.mkdir('logs')
            file_handler = RotatingFileHandler('logs/poker_analytics.log', maxBytes=10240000, backupCount=10)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)

            app.logger.setLevel(logging.INFO)
            app.logger.info('Poker Analytics startup')

    # Register routes
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(poker_identity_bp, url_prefix="/api/player-identity-claims")
    app.register_blueprint(live_game_bp, url_prefix="/api")
    app.register_blueprint(live_game_sse_bp, url_prefix="/api")  # SSE real-time updates
    app.register_blueprint(game_bp, url_prefix="/api/games")
    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(bug_report_bp, url_prefix="/api")
    app.register_blueprint(rules_bp, url_prefix="/api")

    # Set up audit middleware
    app.before_request(setup_request_audit_context)
    app.teardown_appcontext(teardown_request_audit_context)

    # Database session cleanup
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """
        Clean up database sessions after each request.

        This ensures database connections are properly returned to the pool
        and prevents connection leaks.
        """
        from db.database import SessionLocal
        if hasattr(SessionLocal, 'remove'):
            SessionLocal.remove()

    return app

# Create app instance for gunicorn
app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    flask_env = os.getenv("FLASK_ENV", "development")
    debug_mode = flask_env == "development"

    app.run(host="0.0.0.0", port=port, debug=debug_mode)