"""
Authentication domain service.

This module provides the core business logic for user authentication,
including registration and login operations.
"""

from datetime import datetime, timezone
from domain.shared.password_hasher import PasswordHasher
from domain.shared.result import Result
from ..value_objects.email import Email


class AuthenticationService:
    """
    Domain service for user authentication operations.

    This service encapsulates the business logic for user registration
    and login, coordinating between password hashing and user persistence.

    The service uses dependency injection for testability and follows
    the domain-driven design pattern of keeping business logic separate
    from infrastructure concerns.

    Attributes:
        password_hasher: Service for hashing and verifying passwords
        user_repository: Repository for user persistence operations
    """

    # Password constraints
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 72  # Bcrypt limitation

    def __init__(self, password_hasher: PasswordHasher, user_repository):
        """
        Initialize the authentication service.

        Args:
            password_hasher: Password hashing service implementation
            user_repository: User repository for persistence operations
        """
        self.password_hasher = password_hasher
        self.user_repository = user_repository

    def register(self, email: Email, password: str, display_name: str) -> Result:
        """
        Register a new user account.

        This method handles the complete registration process:
        1. Validates password requirements
        2. Checks for duplicate email
        3. Hashes the password
        4. Creates the user entity
        5. Persists via repository

        Args:
            email: User's email address (validated Email value object)
            password: Plaintext password (will be hashed)
            display_name: User's display name

        Returns:
            Result containing the created User on success, or error message on failure

        Example:
            >>> email = Email("user@example.com")
            >>> result = auth_service.register(email, "SecurePass123!", "John Doe")
            >>> if result.is_success():
            >>>     user = result.value
            >>>     print(f"User {user.id} registered")
            >>> else:
            >>>     print(f"Registration failed: {result.error}")
        """
        # Validate password length
        if not password:
            return Result.failure("Password cannot be empty")

        if len(password) < self.MIN_PASSWORD_LENGTH:
            return Result.failure(
                f"Password must be at least {self.MIN_PASSWORD_LENGTH} characters"
            )

        if len(password) > self.MAX_PASSWORD_LENGTH:
            return Result.failure(
                f"Password cannot exceed {self.MAX_PASSWORD_LENGTH} characters"
            )

        # Validate display name
        if not display_name or not display_name.strip():
            return Result.failure("Display name cannot be empty")

        display_name = display_name.strip()
        if len(display_name) > 100:
            return Result.failure("Display name cannot exceed 100 characters")

        # Check for duplicate email
        normalized_email = email.normalized()
        existing_user = self.user_repository.find_by_email(normalized_email)
        if existing_user:
            return Result.failure("Email already registered")

        # Hash password
        try:
            password_hash = self.password_hasher.hash(password)
        except Exception as e:
            return Result.failure(f"Failed to process password: {str(e)}")

        # Create user entity
        try:
            user = self.user_repository.create(
                email=normalized_email,
                password_hash=password_hash,
                display_name=display_name,
                email_verified=False
            )
            return Result.success(user)
        except Exception as e:
            return Result.failure(f"Failed to create user: {str(e)}")

    def login(self, email: Email, password: str) -> Result:
        """
        Authenticate a user with email and password.

        This method handles the complete login process:
        1. Finds user by email
        2. Verifies password
        3. Updates last_login_at timestamp
        4. Returns authenticated user

        Args:
            email: User's email address (validated Email value object)
            password: Plaintext password to verify

        Returns:
            Result containing the authenticated User on success, or error message on failure

        Example:
            >>> email = Email("user@example.com")
            >>> result = auth_service.login(email, "SecurePass123!")
            >>> if result.is_success():
            >>>     user = result.value
            >>>     print(f"User {user.email} logged in")
            >>> else:
            >>>     print(f"Login failed: {result.error}")

        Note:
            Returns generic "Invalid credentials" error for both non-existent users
            and incorrect passwords to prevent email enumeration attacks.
        """
        # Validate password not empty
        if not password:
            return Result.failure("Password cannot be empty")

        # Find user by email
        normalized_email = email.normalized()
        user = self.user_repository.find_by_email(normalized_email)

        if not user:
            # Return generic error to prevent email enumeration
            return Result.failure("Invalid credentials")

        # Verify password
        try:
            is_valid = self.password_hasher.verify(password, user.password_hash)
        except Exception as e:
            return Result.failure(f"Failed to verify password: {str(e)}")

        if not is_valid:
            return Result.failure("Invalid credentials")

        # Update last login timestamp
        try:
            user.last_login_at = datetime.now(timezone.utc)
            self.user_repository.update(user)
        except Exception as e:
            # Login succeeded but timestamp update failed - log but don't fail login
            # In production, this should be logged
            pass

        return Result.success(user)
