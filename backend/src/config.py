import os
import sys
import logging

# Required environment variables for production
REQUIRED_ENV_VARS = [
    'DATABASE_URL',
]

# Required for production environment
PRODUCTION_REQUIRED_ENV_VARS = [
    'DATABASE_URL',
    'ALLOWED_ORIGINS',
    'FLASK_ENV',
]

def validate_environment():
    """Validate that all required environment variables are set."""
    flask_env = os.getenv("FLASK_ENV", "development")

    # Check basic required variables
    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]

    # Additional checks for production
    if flask_env == "production":
        missing.extend([var for var in PRODUCTION_REQUIRED_ENV_VARS if not os.getenv(var)])

        # Warn about default values in production
        if os.getenv("ALLOWED_ORIGINS") == "http://localhost:3000":
            logging.warning("ALLOWED_ORIGINS is set to localhost in production!")

    if missing:
        logging.error(f"Missing required environment variables: {', '.join(missing)}")
        if flask_env == "production":
            sys.exit(1)
        else:
            logging.warning("Running in development mode with missing variables")

# Configuration values
SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
SQLALCHEMY_TRACK_MODIFICATIONS = False
PORT = int(os.getenv("PORT", "8000"))

# Validate environment on import
validate_environment()
