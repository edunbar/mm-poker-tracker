"""
Password strength validation service.

This module provides password strength validation with scoring and feedback
to help users create secure passwords.
"""

import re
from typing import Dict, List, Any


# Common passwords list (top 100 most common)
COMMON_PASSWORDS = {
    'password', '123456', '123456789', '12345678', '12345', '1234567', 'password1',
    '1234567890', 'abc123', '111111', '123123', 'admin', 'letmein', 'welcome',
    'monkey', '1234', 'qwerty', 'dragon', 'master', 'baseball', 'iloveyou',
    'trustno1', '1q2w3e4r', 'sunshine', 'princess', 'football', 'shadow',
    'michael', 'jennifer', 'superman', 'batman', 'tigger', 'jordan', 'soccer',
    'pepper', 'cheese', 'summer', 'ashley', 'nicole', 'jessica', 'hello',
    'andrew', 'charlie', 'cowboy', 'dallas', 'rangers', 'starwars', 'klaster',
    'zaq1zaq1', 'killer', 'freedom', 'whatever', 'jordan23', 'harley', 'robert',
    'matthew', 'daniel', '123qwe', 'killer', 'trustno1', 'ranger', 'buster',
    'thomas', 'robert', 'hockey', 'ranger', 'daniel', 'starwars', 'klaster',
    '112233', 'george', 'computer', 'michelle', 'jessica', 'pepper', 'zaq1zaq1',
    'hunter', 'banana', 'chelsea', 'mustang', 'steelers', 'melissa', 'yankees',
    'cookie', 'secret', 'love', 'hannah', 'test', 'test123', 'password123',
    'admin123', 'root', 'toor', 'pass', 'pass123', 'passw0rd', 'password!',
    'welcome1', 'welcome123', 'qwerty123', 'abc123', '123abc'
}


def calculate_password_strength(password: str) -> Dict[str, Any]:
    """
    Calculate password strength and provide feedback.

    Args:
        password: The password to evaluate

    Returns:
        Dictionary containing:
        - score: Strength score from 0-100
        - strength: Text description ('weak', 'fair', 'good', 'strong')
        - feedback: List of improvement suggestions
        - meets_requirements: Boolean indicating if minimum requirements are met
        - details: Breakdown of what criteria are met
    """
    if not password:
        return {
            'score': 0,
            'strength': 'weak',
            'feedback': ['Password is required'],
            'meets_requirements': False,
            'details': {}
        }

    score = 0
    feedback = []
    details = {}

    # Check length (30 points max)
    length = len(password)
    details['length'] = length

    if length < 8:
        feedback.append('Password must be at least 8 characters long')
    elif length >= 8 and length < 12:
        score += 15
        feedback.append('Consider using a longer password (12+ characters) for better security')
    elif length >= 12 and length < 16:
        score += 25
    else:  # 16+
        score += 30
        details['has_good_length'] = True

    if length > 72:
        feedback.append('Password is too long (maximum 72 characters for bcrypt)')
        return {
            'score': 0,
            'strength': 'weak',
            'feedback': feedback,
            'meets_requirements': False,
            'details': details
        }

    # Check for lowercase letters (15 points)
    has_lowercase = bool(re.search(r'[a-z]', password))
    details['has_lowercase'] = has_lowercase
    if has_lowercase:
        score += 15
    else:
        feedback.append('Add lowercase letters (a-z)')

    # Check for uppercase letters (15 points)
    has_uppercase = bool(re.search(r'[A-Z]', password))
    details['has_uppercase'] = has_uppercase
    if has_uppercase:
        score += 15
    else:
        feedback.append('Add uppercase letters (A-Z)')

    # Check for numbers (15 points)
    has_numbers = bool(re.search(r'[0-9]', password))
    details['has_numbers'] = has_numbers
    if has_numbers:
        score += 15
    else:
        feedback.append('Add numbers (0-9)')

    # Check for special characters (15 points)
    has_special = bool(re.search(r'[^a-zA-Z0-9]', password))
    details['has_special'] = has_special
    if has_special:
        score += 15
    else:
        feedback.append('Add special characters (!@#$%^&*)')

    # Check against common passwords (10 points deduction)
    is_common = password.lower() in COMMON_PASSWORDS
    details['is_common'] = is_common
    if is_common:
        score = max(0, score - 30)
        feedback.append('This is a commonly used password. Choose something more unique.')

    # Check for repeated characters
    has_repeats = bool(re.search(r'(.)\1{2,}', password))
    details['has_repeats'] = has_repeats
    if has_repeats:
        score = max(0, score - 10)
        feedback.append('Avoid repeating the same character multiple times')

    # Check for sequential characters (123, abc, etc.)
    has_sequences = any([
        '123' in password, '234' in password, '345' in password,
        'abc' in password.lower(), 'bcd' in password.lower(), 'cde' in password.lower(),
        'qwerty' in password.lower(), 'asdf' in password.lower()
    ])
    details['has_sequences'] = has_sequences
    if has_sequences:
        score = max(0, score - 10)
        feedback.append('Avoid sequential characters (123, abc, qwerty)')

    # Determine strength category
    if score >= 80:
        strength = 'strong'
    elif score >= 60:
        strength = 'good'
    elif score >= 40:
        strength = 'fair'
    else:
        strength = 'weak'

    # Check if minimum requirements are met
    meets_requirements = (
        length >= 8 and
        length <= 72 and
        has_lowercase and
        has_uppercase and
        has_numbers and
        not is_common
    )

    # Add positive feedback if strong
    if score >= 80:
        feedback = ['Your password is strong!'] + feedback

    return {
        'score': min(100, score),
        'strength': strength,
        'feedback': feedback if feedback else ['Your password meets security requirements'],
        'meets_requirements': meets_requirements,
        'details': details
    }


def validate_password_for_registration(password: str) -> tuple[bool, List[str]]:
    """
    Validate password meets minimum requirements for registration.

    Args:
        password: The password to validate

    Returns:
        Tuple of (is_valid, error_messages)
        - is_valid: True if password meets all requirements
        - error_messages: List of validation errors (empty if valid)
    """
    errors = []

    # Check length
    if not password:
        errors.append('Password is required')
        return False, errors

    if len(password) < 8:
        errors.append('Password must be at least 8 characters long')

    if len(password) > 72:
        errors.append('Password must not exceed 72 characters')

    # Check character requirements
    if not re.search(r'[a-z]', password):
        errors.append('Password must contain at least one lowercase letter')

    if not re.search(r'[A-Z]', password):
        errors.append('Password must contain at least one uppercase letter')

    if not re.search(r'[0-9]', password):
        errors.append('Password must contain at least one number')

    # Check against common passwords
    if password.lower() in COMMON_PASSWORDS:
        errors.append('This password is too common. Please choose a more unique password')

    return len(errors) == 0, errors


def get_password_requirements() -> Dict[str, Any]:
    """
    Get the password requirements for the application.

    Returns:
        Dictionary describing password requirements
    """
    return {
        'min_length': 8,
        'max_length': 72,
        'requires_lowercase': True,
        'requires_uppercase': True,
        'requires_numbers': True,
        'requires_special': False,  # Recommended but not required
        'disallow_common': True
    }
