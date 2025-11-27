"""
Flask-Limiter instance for rate limiting across the application.

This module is separate from app.py to avoid circular imports.
Blueprints can import limiter from here, and app.py initializes it.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Create limiter instance
# Will be initialized with the Flask app in app.py's create_app()
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=["200 per hour", "50 per minute"],
    strategy="fixed-window"
)
