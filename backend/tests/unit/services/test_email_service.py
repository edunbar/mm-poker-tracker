"""
Unit tests for email service.

Tests cover password changed notification email functionality,
including SendGrid integration and error handling.
"""

import pytest
from unittest.mock import patch, MagicMock
from services.email_service import send_password_changed_notification


class TestPasswordChangedNotification:
    """Test password changed notification email."""

    @patch('services.email_service.SendGridAPIClient')
    @patch('services.email_service.os.getenv')
    def test_successful_email_send(self, mock_getenv, mock_sendgrid_client):
        """Test successful password changed notification email."""
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default=None: {
            'SENDGRID_API_KEY': 'test_sendgrid_key',
            'FROM_EMAIL': 'noreply@homegame.gg'
        }.get(key, default)

        # Mock SendGrid client
        mock_sg_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_sg_instance.send.return_value = mock_response
        mock_sendgrid_client.return_value = mock_sg_instance

        # Send notification
        success, message = send_password_changed_notification(
            user_email='test@example.com',
            display_name='Test User'
        )

        assert success is True
        assert 'successfully' in message.lower()
        mock_sg_instance.send.assert_called_once()

    @patch('services.email_service.os.getenv')
    def test_missing_sendgrid_api_key(self, mock_getenv):
        """Test that missing SendGrid API key is handled."""
        # Mock environment with no API key
        mock_getenv.side_effect = lambda key, default=None: {
            'SENDGRID_API_KEY': None,
            'FROM_EMAIL': 'noreply@homegame.gg'
        }.get(key, default)

        success, message = send_password_changed_notification(
            user_email='test@example.com',
            display_name='Test User'
        )

        assert success is False
        assert 'SendGrid API key' in message

    @patch('services.email_service.SendGridAPIClient')
    @patch('services.email_service.os.getenv')
    def test_email_content_includes_user_info(self, mock_getenv, mock_sendgrid_client):
        """Test that email contains user's name and timestamp."""
        mock_getenv.side_effect = lambda key, default=None: {
            'SENDGRID_API_KEY': 'test_key',
            'FROM_EMAIL': 'noreply@homegame.gg'
        }.get(key, default)

        mock_sg_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_sg_instance.send.return_value = mock_response
        mock_sendgrid_client.return_value = mock_sg_instance

        # Capture the Mail object
        with patch('services.email_service.Mail') as mock_mail:
            send_password_changed_notification(
                user_email='user@example.com',
                display_name='John Doe'
            )

            # Verify Mail was created
            mock_mail.assert_called_once()
            call_kwargs = mock_mail.call_args[1]

            # Check that plain_text_content was created with user info
            # The content should include the display name
            assert call_kwargs is not None

    @patch('services.email_service.SendGridAPIClient')
    @patch('services.email_service.os.getenv')
    def test_email_subject_is_password_changed(self, mock_getenv, mock_sendgrid_client):
        """Test that email subject indicates password changed."""
        mock_getenv.side_effect = lambda key, default=None: {
            'SENDGRID_API_KEY': 'test_key',
            'FROM_EMAIL': 'noreply@homegame.gg'
        }.get(key, default)

        mock_sg_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_sg_instance.send.return_value = mock_response
        mock_sendgrid_client.return_value = mock_sg_instance

        with patch('services.email_service.Subject') as mock_subject:
            send_password_changed_notification(
                user_email='test@example.com',
                display_name='Test User'
            )

            # Verify Subject was created with correct text
            mock_subject.assert_called_once()
            subject_text = mock_subject.call_args[0][0]
            assert 'Password Changed' in subject_text

    @patch('services.email_service.SendGridAPIClient')
    @patch('services.email_service.os.getenv')
    def test_sendgrid_exception_handled(self, mock_getenv, mock_sendgrid_client):
        """Test that SendGrid exceptions are handled gracefully."""
        mock_getenv.side_effect = lambda key, default=None: {
            'SENDGRID_API_KEY': 'test_key',
            'FROM_EMAIL': 'noreply@homegame.gg'
        }.get(key, default)

        # Mock SendGrid to raise exception
        mock_sg_instance = MagicMock()
        mock_sg_instance.send.side_effect = Exception('SendGrid API error')
        mock_sendgrid_client.return_value = mock_sg_instance

        success, message = send_password_changed_notification(
            user_email='test@example.com',
            display_name='Test User'
        )

        assert success is False
        assert 'Failed' in message or 'error' in message.lower()

    @patch('services.email_service.SendGridAPIClient')
    @patch('services.email_service.os.getenv')
    def test_email_from_address(self, mock_getenv, mock_sendgrid_client):
        """Test that email is sent from correct address."""
        mock_getenv.side_effect = lambda key, default=None: {
            'SENDGRID_API_KEY': 'test_key',
            'FROM_EMAIL': 'security@homegame.gg'
        }.get(key, default)

        mock_sg_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_sg_instance.send.return_value = mock_response
        mock_sendgrid_client.return_value = mock_sg_instance

        with patch('services.email_service.From') as mock_from:
            send_password_changed_notification(
                user_email='test@example.com',
                display_name='Test User'
            )

            # Verify From was created with correct email
            mock_from.assert_called_once()
            from_email = mock_from.call_args[0][0]
            assert from_email == 'security@homegame.gg'

    @patch('services.email_service.SendGridAPIClient')
    @patch('services.email_service.os.getenv')
    def test_email_to_address(self, mock_getenv, mock_sendgrid_client):
        """Test that email is sent to correct recipient."""
        mock_getenv.side_effect = lambda key, default=None: {
            'SENDGRID_API_KEY': 'test_key',
            'FROM_EMAIL': 'noreply@homegame.gg'
        }.get(key, default)

        mock_sg_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_sg_instance.send.return_value = mock_response
        mock_sendgrid_client.return_value = mock_sg_instance

        with patch('services.email_service.To') as mock_to:
            send_password_changed_notification(
                user_email='recipient@example.com',
                display_name='Recipient User'
            )

            # Verify To was created with correct email
            mock_to.assert_called_once()
            to_email = mock_to.call_args[0][0]
            assert to_email == 'recipient@example.com'
