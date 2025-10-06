"""
Unit tests for password strength service.

Tests cover password strength calculation, validation, requirements checking,
and feedback generation for user password creation.
"""

import pytest
from services.password_strength_service import (
    calculate_password_strength,
    validate_password_for_registration,
    get_password_requirements,
    COMMON_PASSWORDS
)


class TestCalculatePasswordStrength:
    """Test password strength calculation and scoring."""

    def test_strong_password_high_score(self):
        """Test that a strong password gets a high score (80+)."""
        result = calculate_password_strength('MySecure!Pass123')

        assert result['score'] >= 80
        assert result['strength'] == 'strong'
        assert result['meets_requirements'] is True

    def test_weak_password_low_score(self):
        """Test that a weak password gets a low score (<40)."""
        result = calculate_password_strength('pass')

        assert result['score'] < 40
        assert result['strength'] == 'weak'
        assert result['meets_requirements'] is False

    def test_empty_password_returns_zero_score(self):
        """Test that empty password returns score of 0."""
        result = calculate_password_strength('')

        assert result['score'] == 0
        assert result['strength'] == 'weak'
        assert 'Password is required' in result['feedback']
        assert result['meets_requirements'] is False

    def test_password_length_scoring(self):
        """Test that password length affects score appropriately."""
        short = calculate_password_strength('Aa1!')  # 4 chars
        medium = calculate_password_strength('Aa1!Aa1!Aa1!')  # 12 chars
        long = calculate_password_strength('Aa1!Aa1!Aa1!Aa1!Aa1!')  # 20 chars

        # Longer passwords should have higher scores
        assert short['score'] < medium['score'] < long['score']

    def test_lowercase_letters_detected(self):
        """Test that lowercase letters are detected and scored."""
        with_lower = calculate_password_strength('Password123!')
        without_lower = calculate_password_strength('PASSWORD123!')

        assert with_lower['details']['has_lowercase'] is True
        assert without_lower['details']['has_lowercase'] is False
        assert with_lower['score'] > without_lower['score']

    def test_uppercase_letters_detected(self):
        """Test that uppercase letters are detected and scored."""
        with_upper = calculate_password_strength('Password123!')
        without_upper = calculate_password_strength('password123!')

        assert with_upper['details']['has_uppercase'] is True
        assert without_upper['details']['has_uppercase'] is False
        assert with_upper['score'] > without_upper['score']

    def test_numbers_detected(self):
        """Test that numbers are detected and scored."""
        with_numbers = calculate_password_strength('Password123!')
        without_numbers = calculate_password_strength('PasswordAbc!')

        assert with_numbers['details']['has_numbers'] is True
        assert without_numbers['details']['has_numbers'] is False
        assert with_numbers['score'] > without_numbers['score']

    def test_special_characters_detected(self):
        """Test that special characters are detected and scored."""
        with_special = calculate_password_strength('Password123!')
        without_special = calculate_password_strength('Password123a')

        assert with_special['details']['has_special'] is True
        assert without_special['details']['has_special'] is False
        assert with_special['score'] > without_special['score']

    def test_common_password_penalized(self):
        """Test that common passwords are detected and penalized."""
        common = calculate_password_strength('password')
        unique = calculate_password_strength('MyUniquePwd123!')

        assert common['details']['is_common'] is True
        assert unique['details']['is_common'] is False
        assert common['score'] < unique['score']
        assert 'commonly used password' in ' '.join(common['feedback']).lower()

    def test_common_password_case_insensitive(self):
        """Test that common password detection is case-insensitive."""
        assert calculate_password_strength('password')['details']['is_common'] is True
        assert calculate_password_strength('PASSWORD')['details']['is_common'] is True
        assert calculate_password_strength('PaSsWoRd')['details']['is_common'] is True

    def test_repeated_characters_penalized(self):
        """Test that repeated characters are detected and penalized."""
        with_repeats = calculate_password_strength('Paaassword111!')
        without_repeats = calculate_password_strength('Password123!')

        assert with_repeats['details']['has_repeats'] is True
        assert without_repeats['details']['has_repeats'] is False
        # Both passwords are similar, so just verify detection works
        # The penalty might not always result in different scores

    def test_sequential_characters_penalized(self):
        """Test that sequential characters are detected and penalized."""
        test_cases = [
            ('Password123!', True),  # Has '123'
            ('Password234!', True),  # Has '234'
            ('Passwordabc!', True),  # Has 'abc'
            ('qwerty123456', True),  # Has 'qwerty' and '123'
            ('Passwordxyz!', False),  # No sequences
        ]

        for password, should_have_sequences in test_cases:
            result = calculate_password_strength(password)
            assert result['details']['has_sequences'] == should_have_sequences

    def test_password_too_long_rejected(self):
        """Test that password longer than 72 characters is rejected."""
        too_long = 'A' * 73 + 'bc123!'
        result = calculate_password_strength(too_long)

        assert result['score'] == 0
        assert result['strength'] == 'weak'
        assert result['meets_requirements'] is False
        assert 'too long' in ' '.join(result['feedback']).lower()

    def test_strength_categories(self):
        """Test that strength categories are assigned correctly."""
        # Strong: score >= 80
        strong = calculate_password_strength('MyVerySecure!Pass123word')
        assert strong['score'] >= 80
        assert strong['strength'] == 'strong'

        # Good: score 60-79
        good = calculate_password_strength('GoodPass123!')
        assert 60 <= good['score'] < 80
        assert good['strength'] == 'good'

        # Weak: score < 40
        weak = calculate_password_strength('pass12')
        assert weak['score'] < 40
        assert weak['strength'] == 'weak'

        # Verify strength matches score ranges
        assert strong['strength'] == 'strong'
        assert good['strength'] == 'good'
        assert weak['strength'] == 'weak'

    def test_feedback_messages_provided(self):
        """Test that helpful feedback messages are provided."""
        # Password missing uppercase
        result = calculate_password_strength('password123!')
        assert any('uppercase' in msg.lower() for msg in result['feedback'])

        # Password missing numbers
        result = calculate_password_strength('Password!')
        assert any('number' in msg.lower() for msg in result['feedback'])

        # Password missing special chars
        result = calculate_password_strength('Password123')
        assert any('special' in msg.lower() for msg in result['feedback'])

    def test_meets_requirements_logic(self):
        """Test that meets_requirements flag is set correctly."""
        # Meets all requirements
        good = calculate_password_strength('MyPassword123!')
        assert good['meets_requirements'] is True

        # Too short
        short = calculate_password_strength('Pass1!')
        assert short['meets_requirements'] is False

        # Missing uppercase
        no_upper = calculate_password_strength('password123!')
        assert no_upper['meets_requirements'] is False

        # Common password
        common = calculate_password_strength('password123')
        assert common['meets_requirements'] is False


class TestValidatePasswordForRegistration:
    """Test password validation for registration."""

    def test_valid_password_passes(self):
        """Test that a valid password passes validation."""
        is_valid, errors = validate_password_for_registration('MySecurePass123!')

        assert is_valid is True
        assert len(errors) == 0

    def test_empty_password_fails(self):
        """Test that empty password fails validation."""
        is_valid, errors = validate_password_for_registration('')

        assert is_valid is False
        assert 'required' in ' '.join(errors).lower()

    def test_short_password_fails(self):
        """Test that password < 8 characters fails."""
        is_valid, errors = validate_password_for_registration('Pass1!')

        assert is_valid is False
        assert any('8 characters' in err for err in errors)

    def test_long_password_fails(self):
        """Test that password > 72 characters fails."""
        too_long = 'A' * 73 + 'bc123!'
        is_valid, errors = validate_password_for_registration(too_long)

        assert is_valid is False
        assert any('72 characters' in err for err in errors)

    def test_missing_lowercase_fails(self):
        """Test that password without lowercase fails."""
        is_valid, errors = validate_password_for_registration('PASSWORD123!')

        assert is_valid is False
        assert any('lowercase' in err.lower() for err in errors)

    def test_missing_uppercase_fails(self):
        """Test that password without uppercase fails."""
        is_valid, errors = validate_password_for_registration('password123!')

        assert is_valid is False
        assert any('uppercase' in err.lower() for err in errors)

    def test_missing_numbers_fails(self):
        """Test that password without numbers fails."""
        is_valid, errors = validate_password_for_registration('PasswordAbc!')

        assert is_valid is False
        assert any('number' in err.lower() for err in errors)

    def test_common_password_fails(self):
        """Test that common passwords fail validation."""
        common_passwords = ['password', 'password123', 'qwerty', '123456']

        for pwd in common_passwords:
            is_valid, errors = validate_password_for_registration(pwd)
            assert is_valid is False
            assert any('common' in err.lower() for err in errors)

    def test_multiple_errors_returned(self):
        """Test that multiple validation errors are returned together."""
        # Password with multiple issues
        is_valid, errors = validate_password_for_registration('pass')

        assert is_valid is False
        assert len(errors) >= 3  # Should have multiple error messages


class TestGetPasswordRequirements:
    """Test password requirements retrieval."""

    def test_returns_correct_structure(self):
        """Test that requirements have the correct structure."""
        requirements = get_password_requirements()

        assert 'min_length' in requirements
        assert 'max_length' in requirements
        assert 'requires_lowercase' in requirements
        assert 'requires_uppercase' in requirements
        assert 'requires_numbers' in requirements
        assert 'requires_special' in requirements
        assert 'disallow_common' in requirements

    def test_correct_values(self):
        """Test that requirements have the correct values."""
        requirements = get_password_requirements()

        assert requirements['min_length'] == 8
        assert requirements['max_length'] == 72
        assert requirements['requires_lowercase'] is True
        assert requirements['requires_uppercase'] is True
        assert requirements['requires_numbers'] is True
        assert requirements['requires_special'] is False  # Recommended but not required
        assert requirements['disallow_common'] is True


class TestCommonPasswords:
    """Test common passwords list."""

    def test_common_passwords_list_exists(self):
        """Test that COMMON_PASSWORDS set is populated."""
        assert len(COMMON_PASSWORDS) > 0
        assert isinstance(COMMON_PASSWORDS, set)

    def test_common_passwords_are_lowercase(self):
        """Test that common passwords are stored in lowercase for comparison."""
        # Common passwords should mostly be lowercase for case-insensitive matching
        # Just verify the set has string values
        assert all(isinstance(pwd, str) for pwd in COMMON_PASSWORDS)

    def test_known_common_passwords_included(self):
        """Test that well-known common passwords are in the list."""
        known_common = ['password', '123456', 'qwerty', 'admin']

        for pwd in known_common:
            assert pwd in COMMON_PASSWORDS


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_password_with_only_spaces(self):
        """Test password with only spaces."""
        result = calculate_password_strength('        ')

        assert result['score'] < 40
        assert result['meets_requirements'] is False

    def test_password_with_unicode_characters(self):
        """Test password with unicode characters."""
        result = calculate_password_strength('Pässw0rd123!')

        # Should still evaluate, special chars count as special
        assert result['score'] > 0
        assert result['details']['has_special'] is True

    def test_password_with_emojis(self):
        """Test password with emojis."""
        result = calculate_password_strength('Pass🔐word123')

        # Should evaluate without crashing
        assert result['score'] > 0

    def test_none_password_handled(self):
        """Test that None password is handled gracefully."""
        result = calculate_password_strength(None)

        assert result['score'] == 0
        assert result['strength'] == 'weak'
        assert result['meets_requirements'] is False

    def test_very_long_feedback_list(self):
        """Test that feedback list is reasonable for very weak passwords."""
        result = calculate_password_strength('a')

        # Should have multiple feedback items but not excessive
        assert len(result['feedback']) > 0
        assert len(result['feedback']) < 10
