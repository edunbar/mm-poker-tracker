from flask import Blueprint, jsonify
from db.database import SessionLocal
from sqlalchemy import text
import logging
import os
from datetime import datetime

health_bp = Blueprint('health', __name__)

@health_bp.route('/health')
def health_check():
    """Basic health check endpoint."""
    try:
        # Test database connection
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))

        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "environment": os.getenv("FLASK_ENV", "development"),
            "services": {
                "database": "connected"
            }
        }), 200

    except Exception as e:
        logging.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "services": {
                "database": "disconnected"
            }
        }), 500

@health_bp.route('/health/ready')
def readiness_check():
    """Kubernetes readiness probe endpoint."""
    try:
        # Check database connectivity
        with SessionLocal() as db:
            result = db.execute(text("SELECT COUNT(*) FROM games")).scalar()

        return jsonify({
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": "ready",
                "games_table": "accessible"
            }
        }), 200

    except Exception as e:
        logging.error(f"Readiness check failed: {e}")
        return jsonify({
            "status": "not_ready",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }), 503

@health_bp.route('/health/live')
def liveness_check():
    """Kubernetes liveness probe endpoint."""
    return jsonify({
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": "running"
    }), 200

@health_bp.route('/metrics')
def metrics():
    """Basic metrics endpoint."""
    try:
        with SessionLocal() as db:
            games_count = db.execute(text("SELECT COUNT(*) FROM games")).scalar()
            players_count = db.execute(text("SELECT COUNT(*) FROM players")).scalar()
            sessions_count = db.execute(text("SELECT COUNT(*) FROM sessions")).scalar()

        return jsonify({
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "total_games": games_count,
                "total_players": players_count,
                "total_sessions": sessions_count
            }
        }), 200

    except Exception as e:
        logging.error(f"Metrics endpoint failed: {e}")
        return jsonify({
            "error": "Unable to fetch metrics",
            "timestamp": datetime.utcnow().isoformat()
        }), 500