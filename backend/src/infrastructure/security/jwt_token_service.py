"""
JWT token service for authentication.

This module provides JWT token generation and validation for user authentication.
It uses HS256 algorithm with a configurable secret key and expiration time.
"""

import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any


class JWTTokenService:
    """
    Service for generating and validating JWT access tokens.

    This service handles JWT token operations for user authentication, including
    token generation with configurable expiry and safe token validation that
    never raises exceptions.

    Features:
    - HS256 algorithm (HMAC with SHA-256)
    - Configurable token expiry (default 7 days)
    - Graceful error handling (returns None on any error)
    - Environment-based secret key configuration

    Example:
        >>> service = JWTTokenService()
        >>> token = service.generate_access_token("user_123", "user@example.com")
        >>> payload = service.decode_token(token)
        >>> print(payload)
        {'user_id': 'user_123', 'email': 'user@example.com', 'iat': ..., 'exp': ...}
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        token_expiry_days: int = 7
    ) -> None:
        """
        Initialize the JWT token service.

        Args:
            secret_key: Secret key for signing tokens. If not provided, reads from
                       JWT_SECRET environment variable. Should be a long random string.
            token_expiry_days: Number of days until token expires. Default is 7 days.

        Raises:
            ValueError: If secret_key is not provided and JWT_SECRET env var is not set,
                       OR if token_expiry_days is less than 1.

        Note:
            In production, always set JWT_SECRET environment variable.
            Generate a secure secret using: python -c "import secrets; print(secrets.token_urlsafe(64))"
        """
        if token_expiry_days < 1:
            raise ValueError("token_expiry_days must be at least 1")

        self.secret_key = secret_key or os.getenv('JWT_SECRET')
        if not self.secret_key:
            raise ValueError(
                "JWT secret key not provided. Set JWT_SECRET environment variable "
                "or pass secret_key parameter."
            )

        self.token_expiry_days = token_expiry_days
        self.algorithm = 'HS256'

    def generate_access_token(self, user_id: str, email: str) -> str:
        """
        Generate a JWT access token for a user.

        Args:
            user_id: Unique identifier for the user (UUID)
            email: User's email address

        Returns:
            Encoded JWT token as a string

        Raises:
            ValueError: If user_id or email is empty

        Note:
            The token payload includes:
            - user_id: User identifier
            - email: User email
            - iat: Issued at timestamp (UTC)
            - exp: Expiration timestamp (UTC)
        """
        if not user_id:
            raise ValueError("user_id cannot be empty")
        if not email:
            raise ValueError("email cannot be empty")

        now = datetime.now(timezone.utc)
        expiry = now + timedelta(days=self.token_expiry_days)

        payload = {
            'user_id': user_id,
            'email': email,
            'iat': now,
            'exp': expiry
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and validate a JWT token.

        This method validates the token signature and expiration, returning
        the decoded payload. It never raises exceptions - all errors result
        in returning None.

        Args:
            token: The JWT token string to decode

        Returns:
            Dictionary containing the token payload if valid, None otherwise.
            Payload includes: user_id, email, iat, exp

        Note:
            Returns None in these cases:
            - Token has expired (ExpiredSignatureError)
            - Token signature is invalid (InvalidSignatureError)
            - Token format is malformed (DecodeError)
            - Token is empty or None
            - Any other validation error
        """
        if not token:
            return None

        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload

        except jwt.ExpiredSignatureError:
            # Token has expired - return None
            return None

        except jwt.InvalidTokenError:
            # Invalid token (bad signature, malformed, etc.) - return None
            return None

        except Exception:
            # Catch any other unexpected errors - return None
            return None
