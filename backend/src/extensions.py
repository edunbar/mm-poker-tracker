"""
Flask extensions initialization.

This module contains Flask extension instances that can be imported
by both the app factory and route modules without circular dependencies.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize limiter at module level for import in routes and app
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://"
)
