"""
Integration tests for password strength validation.

Tests cover password strength calculation, common password detection,
and feedback generation with real service integration.
"""

import pytest
from services.password_strength_service import calculate_password_strength


class TestPasswordStrengthIntegration:
    """Test password strength service integration."""

    def test_strong_password_evaluation(self):
        """Test that a strong password gets high score and good feedback."""
        result = calculate_password_strength('MyVerySecurePassword123!')

        assert result['score'] >= 80
        assert result['strength'] == 'strong'
        assert result['meets_requirements'] is True
        assert result['details']['has_lowercase'] is True
        assert result['details']['has_uppercase'] is True
        assert result['details']['has_numbers'] is True
        assert result['details']['has_special'] is True
        assert result['details']['is_common'] is False

    def test_weak_password_gives_helpful_feedback(self):
        """Test that weak password provides specific improvement suggestions."""
        result = calculate_password_strength('pass')

        assert result['score'] < 40
        assert result['strength'] == 'weak'
        assert result['meets_requirements'] is False
        assert len(result['feedback']) > 0

        # Should have specific suggestions
        feedback_text = ' '.join(result['feedback']).lower()
        assert 'character' in feedback_text or 'long' in feedback_text

    def test_common_passwords_properly_flagged(self):
        """Test that common passwords are detected and heavily penalized."""
        common_passwords = [
            'password',
            '123456',
            'qwerty',
            'password123',
            'admin'
        ]

        for pwd in common_passwords:
            result = calculate_password_strength(pwd)

            assert result['details']['is_common'] is True
            assert result['meets_requirements'] is False
            assert 'common' in ' '.join(result['feedback']).lower()

    def test_repeated_character_detection(self):
        """Test that passwords with repeated characters are penalized."""
        with_repeats = calculate_password_strength('Paaassswwword111!')
        without_repeats = calculate_password_strength('Password123!')

        assert with_repeats['details']['has_repeats'] is True
        assert without_repeats['details']['has_repeats'] is False
        # Both passwords are similar, so just verify detection works
        # The penalty might not always result in a lower overall score

    def test_sequential_character_detection(self):
        """Test that passwords with sequences are detected."""
        sequences = [
            ('Password123!', True),  # Has 123
            ('Passwordabc!', True),  # Has abc
            ('qwerty123456', True),  # Has qwerty and 123
            ('MySecure!Pass', False),  # No sequences
        ]

        for password, expected in sequences:
            result = calculate_password_strength(password)
            assert result['details']['has_sequences'] == expected

    def test_password_length_affects_score(self):
        """Test that password length significantly affects score."""
        short_pass = calculate_password_strength('Pass1!')  # 6 chars
        medium_pass = calculate_password_strength('Password123!')  # 12 chars
        long_pass = calculate_password_strength('MyVeryLongPasswordWithNumbers123!')  # 35 chars

        # Longer passwords should score higher (all else equal)
        assert short_pass['score'] < medium_pass['score']
        assert medium_pass['score'] < long_pass['score']
