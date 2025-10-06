# Password Hashing Infrastructure Usage Guide

## Overview

This project uses a domain-driven design pattern for password hashing, with:
- **Abstract interface** in `domain/shared/password_hasher.py`
- **Concrete implementation** in `infrastructure/security/bcrypt_password_hasher.py`

## Quick Start

### 1. Import the Password Hasher

```python
from infrastructure.security import BcryptPasswordHasher

# Create hasher instance (cost_factor defaults to 12)
password_hasher = BcryptPasswordHasher(cost_factor=12)
```

### 2. Hash a Password (User Registration)

```python
from infrastructure.security import BcryptPasswordHasher
from db.models import User
from db.database import get_db

def register_user(email: str, password: str, display_name: str):
    """Register a new user with hashed password."""
    # Hash the password
    hasher = BcryptPasswordHasher()
    password_hash = hasher.hash(password)

    # Create user in database
    db = next(get_db())
    new_user = User(
        email=email,
        password_hash=password_hash,
        display_name=display_name,
        email_verified=False
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user
```

### 3. Verify a Password (User Login)

```python
from infrastructure.security import BcryptPasswordHasher
from db.models import User
from db.database import get_db

def authenticate_user(email: str, password: str):
    """Authenticate user by email and password."""
    # Find user by email
    db = next(get_db())
    user = db.query(User).filter(User.email == email).first()

    if not user:
        return None  # User not found

    # Verify password
    hasher = BcryptPasswordHasher()
    if not hasher.verify(password, user.password_hash):
        return None  # Invalid password

    # Update last_login_at
    from datetime import datetime
    user.last_login_at = datetime.now()
    db.commit()

    return user
```

## Flask Route Examples

### User Registration Endpoint

```python
from flask import Blueprint, request, jsonify
from infrastructure.security import BcryptPasswordHasher
from domain.shared.password_hasher import PasswordHashingError
from db.models import User
from db.database import get_db
from sqlalchemy.exc import IntegrityError

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user account."""
    data = request.get_json()

    # Validate input
    email = data.get('email')
    password = data.get('password')
    display_name = data.get('display_name')

    if not email or not password or not display_name:
        return jsonify({'error': 'Missing required fields'}), 400

    # Validate password strength (example)
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    try:
        # Hash password
        hasher = BcryptPasswordHasher()
        password_hash = hasher.hash(password)

        # Create user
        db = next(get_db())
        new_user = User(
            email=email.lower(),  # Normalize email
            password_hash=password_hash,
            display_name=display_name,
            email_verified=False
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return jsonify({
            'id': str(new_user.id),
            'email': new_user.email,
            'display_name': new_user.display_name,
            'created_at': new_user.created_at.isoformat()
        }), 201

    except IntegrityError:
        db.rollback()
        return jsonify({'error': 'Email already registered'}), 409

    except PasswordHashingError as e:
        return jsonify({'error': 'Failed to process password'}), 500

    except Exception as e:
        db.rollback()
        return jsonify({'error': 'Registration failed'}), 500
```

### User Login Endpoint

```python
from flask import Blueprint, request, jsonify, session
from infrastructure.security import BcryptPasswordHasher
from db.models import User
from db.database import get_db
from datetime import datetime

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and create session."""
    data = request.get_json()

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Missing email or password'}), 400

    try:
        # Find user
        db = next(get_db())
        user = db.query(User).filter(User.email == email.lower()).first()

        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401

        # Verify password
        hasher = BcryptPasswordHasher()
        if not hasher.verify(password, user.password_hash):
            return jsonify({'error': 'Invalid credentials'}), 401

        # Update last login
        user.last_login_at = datetime.now()
        db.commit()

        # Create session (or JWT token)
        session['user_id'] = str(user.id)
        session['email'] = user.email

        return jsonify({
            'id': str(user.id),
            'email': user.email,
            'display_name': user.display_name,
            'email_verified': user.email_verified,
            'last_login_at': user.last_login_at.isoformat()
        }), 200

    except Exception as e:
        return jsonify({'error': 'Login failed'}), 500
```

### Password Change Endpoint

```python
@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    """Change user's password."""
    # Require authentication (implement your auth middleware)
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not current_password or not new_password:
        return jsonify({'error': 'Missing passwords'}), 400

    if len(new_password) < 8:
        return jsonify({'error': 'New password must be at least 8 characters'}), 400

    try:
        db = next(get_db())
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Verify current password
        hasher = BcryptPasswordHasher()
        if not hasher.verify(current_password, user.password_hash):
            return jsonify({'error': 'Current password is incorrect'}), 401

        # Hash and update new password
        user.password_hash = hasher.hash(new_password)
        db.commit()

        return jsonify({'message': 'Password updated successfully'}), 200

    except PasswordHashingError:
        return jsonify({'error': 'Failed to process password'}), 500

    except Exception as e:
        db.rollback()
        return jsonify({'error': 'Password change failed'}), 500
```

## Dependency Injection Pattern

For better testability and flexibility, you can inject the password hasher:

```python
from typing import Optional
from infrastructure.security import BcryptPasswordHasher
from domain.shared import PasswordHasher

class UserService:
    """Service for user operations with dependency injection."""

    def __init__(self, password_hasher: Optional[PasswordHasher] = None):
        """Initialize with optional password hasher for testing."""
        self.password_hasher = password_hasher or BcryptPasswordHasher()

    def register_user(self, email: str, password: str, display_name: str):
        """Register new user."""
        password_hash = self.password_hasher.hash(password)
        # ... rest of registration logic

    def authenticate_user(self, email: str, password: str):
        """Authenticate user."""
        # ... fetch user from database
        return self.password_hasher.verify(password, user.password_hash)
```

## Configuration

### Adjusting Cost Factor

The cost factor determines computation time. Adjust based on your needs:

```python
# Default (balanced)
hasher = BcryptPasswordHasher(cost_factor=12)  # ~300ms

# High security (slower)
hasher = BcryptPasswordHasher(cost_factor=14)  # ~1s

# High throughput (faster, less secure)
hasher = BcryptPasswordHasher(cost_factor=10)  # ~80ms
```

### Environment-based Configuration

```python
import os

cost_factor = int(os.getenv('BCRYPT_COST_FACTOR', 12))
hasher = BcryptPasswordHasher(cost_factor=cost_factor)
```

## Important Notes

### Bcrypt Limitations

1. **72-byte password limit**: Bcrypt truncates passwords longer than 72 bytes
2. **Case-sensitive**: Always normalize user input (e.g., lowercase emails)
3. **Timing**: Higher cost factors increase security but slow down operations

### Security Best Practices

1. **Never store plaintext passwords** - Always hash before storing
2. **Don't log passwords** - Never log passwords or hashes
3. **Use HTTPS** - Transmit passwords only over encrypted connections
4. **Validate password strength** - Enforce minimum length and complexity
5. **Rate limit login attempts** - Prevent brute-force attacks
6. **Salt is automatic** - Bcrypt generates unique salts automatically

### Error Handling

```python
from domain.shared import PasswordHashingError

try:
    password_hash = hasher.hash(user_password)
except ValueError as e:
    # Invalid input (empty password, etc.)
    print(f"Invalid password: {e}")
except PasswordHashingError as e:
    # Hashing operation failed
    print(f"Hashing error: {e.message}")
    if e.original_error:
        print(f"Original error: {e.original_error}")
```

## Testing

Run the comprehensive test suite:

```bash
PYTHONPATH=src python test_password_hashing.py
```

Or integrate into pytest:

```python
from infrastructure.security import BcryptPasswordHasher

def test_password_hashing():
    hasher = BcryptPasswordHasher(cost_factor=10)  # Faster for tests

    password = "TestPassword123"
    password_hash = hasher.hash(password)

    assert hasher.verify(password, password_hash)
    assert not hasher.verify("WrongPassword", password_hash)
```

## Migration from Legacy System

If you have existing passwords hashed with a different algorithm:

1. Add a migration strategy field to User model
2. Re-hash passwords on next successful login
3. Gradually phase out old hashing method

```python
def login_with_migration(email, password):
    user = find_user(email)

    # Check if using old hashing method
    if user.password_version == 'legacy':
        if verify_legacy_hash(password, user.password_hash):
            # Re-hash with bcrypt
            hasher = BcryptPasswordHasher()
            user.password_hash = hasher.hash(password)
            user.password_version = 'bcrypt'
            db.commit()
            return user
    else:
        # Use bcrypt verification
        hasher = BcryptPasswordHasher()
        if hasher.verify(password, user.password_hash):
            return user

    return None
```
