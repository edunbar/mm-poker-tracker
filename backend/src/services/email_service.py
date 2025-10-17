import os
import logging
from datetime import datetime, timedelta, timezone
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From, To, Subject, PlainTextContent, HtmlContent
from flask import render_template

def send_bug_report_email(bug_data):
    """
    Send bug report email to configured recipient using SendGrid

    Args:
        bug_data (dict): Bug report data containing:
            - description: Bug description
            - steps_to_reproduce: Steps to reproduce
            - category: Bug category
            - user_email: Optional user email
            - url: Current page URL
            - user_agent: Browser user agent
            - game_code: Optional game code
            - timestamp: Report timestamp

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Get SendGrid configuration
        sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
        from_email = os.getenv('FROM_EMAIL', 'noreply@homegame.gg')
        bug_report_email = os.getenv('BUG_REPORT_EMAIL')

        if not sendgrid_api_key:
            logging.error("SendGrid API key not configured")
            return False, "Email configuration error: SendGrid API key missing"

        if not bug_report_email:
            logging.error("Bug report email not configured")
            return False, "Email configuration error: Bug report email missing"

        # Format email subject
        subject_text = f"Bug Report - HomeGame.gg"
        if bug_data.get('game_code'):
            subject_text += f" [Game: {bug_data['game_code']}]"

        # Format email body
        body = format_bug_report_email(bug_data)

        # Create SendGrid message
        message = Mail(
            from_email=From(from_email, "HomeGame.gg Bug Reports"),
            to_emails=To(bug_report_email),
            subject=Subject(subject_text),
            plain_text_content=PlainTextContent(body)
        )

        # Send email via SendGrid
        sg = SendGridAPIClient(api_key=sendgrid_api_key)
        response = sg.send(message)

        logging.info(f"Bug report email sent successfully to {bug_report_email} (Status: {response.status_code})")
        return True, "Bug report sent successfully"

    except Exception as e:
        logging.error(f"Failed to send bug report email via SendGrid: {str(e)}")
        return False, f"Failed to send bug report: {str(e)}"

def format_bug_report_email(bug_data):
    """Format the bug report data into email body"""

    timestamp = bug_data.get('timestamp', datetime.utcnow().isoformat())

    body = f"""Bug Report Details
==================

Description:
{bug_data.get('description', 'No description provided')}

Steps to Reproduce:
{bug_data.get('steps_to_reproduce', 'No steps provided')}

Category: {bug_data.get('category', 'Not specified')}

Context Information:
-------------------
• URL: {bug_data.get('url', 'Not provided')}
• Timestamp: {timestamp}
• Browser: {extract_browser_info(bug_data.get('user_agent', ''))}
• User Agent: {bug_data.get('user_agent', 'Not provided')}"""

    # Add game context if available
    if bug_data.get('game_code'):
        body += f"\n• Game Code: {bug_data['game_code']}"

    # Add user email if provided
    if bug_data.get('user_email'):
        body += f"\n• User Email: {bug_data['user_email']}"

    body += f"""

Report Source:
This bug report was submitted via the HomeGame.gg bug report feature.

---
HomeGame.gg Bug Report System
{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"""

    return body

def extract_browser_info(user_agent):
    """Extract readable browser info from user agent string"""
    if not user_agent:
        return "Unknown"

    # Simple browser detection
    if 'Chrome' in user_agent:
        return "Chrome"
    elif 'Firefox' in user_agent:
        return "Firefox"
    elif 'Safari' in user_agent and 'Chrome' not in user_agent:
        return "Safari"
    elif 'Edge' in user_agent:
        return "Edge"
    else:
        return "Other"

def validate_bug_report_data(data):
    """
    Validate bug report data

    Args:
        data (dict): Bug report data

    Returns:
        tuple: (is_valid: bool, errors: list)
    """
    errors = []

    # Required fields
    if not data.get('description') or len(data['description'].strip()) < 10:
        errors.append("Description must be at least 10 characters long")

    if data.get('description') and len(data['description']) > 5000:
        errors.append("Description must be less than 5000 characters")

    if data.get('steps_to_reproduce') and len(data['steps_to_reproduce']) > 3000:
        errors.append("Steps to reproduce must be less than 3000 characters")

    # Email validation if provided
    if data.get('user_email'):
        email = data['user_email'].strip()
        if email and '@' not in email:
            errors.append("Invalid email format")

    # Category validation
    valid_categories = ['UI Issue', 'Functionality', 'Performance', 'Data Accuracy', 'Other']
    if data.get('category') and data['category'] not in valid_categories:
        errors.append(f"Invalid category. Must be one of: {', '.join(valid_categories)}")

    return len(errors) == 0, errors


def send_password_changed_notification(user_email, display_name):
    """
    Send password changed notification email to user using SendGrid.

    This email notifies users that their password was successfully changed
    and advises them to secure their account if they didn't make this change.

    Args:
        user_email (str): User's email address
        display_name (str): User's display name

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Get SendGrid configuration
        sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
        from_email = os.getenv('FROM_EMAIL', 'noreply@homegame.gg')

        if not sendgrid_api_key:
            logging.error("SendGrid API key not configured")
            return False, "Email configuration error: SendGrid API key missing"

        # Format email subject
        subject_text = "Password Changed - HomeGame.gg"

        # Format email body
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        body = f"""Hi {display_name},

This email confirms that your password for HomeGame.gg was successfully changed on {timestamp}.

If you made this change, no further action is required. All your existing sessions have been logged out for security.

If you did NOT make this change:
• Your account may have been compromised
• Please reset your password immediately at https://homegame.gg/forgot-password
• Review your account activity and game access
• Contact support if you need assistance

Security Tips:
• Use a strong, unique password for your account
• Never share your password with anyone
• Enable two-factor authentication if available

---
HomeGame.gg Security Team
This is an automated security notification."""

        # Create SendGrid message
        message = Mail(
            from_email=From(from_email, "HomeGame.gg Security"),
            to_emails=To(user_email),
            subject=Subject(subject_text),
            plain_text_content=PlainTextContent(body)
        )

        # Send email via SendGrid
        sg = SendGridAPIClient(api_key=sendgrid_api_key)
        response = sg.send(message)

        logging.info(f"Password changed notification sent to {user_email} (Status: {response.status_code})")
        return True, "Notification sent successfully"

    except Exception as e:
        logging.error(f"Failed to send password changed notification via SendGrid: {str(e)}")
        # Don't fail the password change if email fails
        return False, f"Failed to send notification: {str(e)}"


def send_password_reset_email(user_email, display_name, reset_token):
    """
    Send password reset email with reset link to user using SendGrid.

    This email provides a secure link for users to reset their password.
    The link contains a time-limited token that expires after 24 hours.

    Args:
        user_email (str): User's email address
        display_name (str): User's display name
        reset_token (str): Secure reset token (will be in URL)

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Get SendGrid configuration
        sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
        from_email = os.getenv('FROM_EMAIL', 'noreply@homegame.gg')
        # Allow override of frontend URL for different environments
        frontend_url = os.getenv('FRONTEND_URL', 'https://homegame.gg')

        if not sendgrid_api_key:
            logging.error("SendGrid API key not configured")
            return False, "Email configuration error: SendGrid API key missing"

        # Format email subject
        subject_text = "Reset Your Password - HomeGame.gg"

        # Create reset URL
        reset_url = f"{frontend_url}/reset-password?token={reset_token}"

        # Format timestamp for email
        current_time_utc = datetime.now(timezone.utc)
        request_time_formatted = current_time_utc.strftime('%Y-%m-%d %H:%M UTC')

        # Plain text fallback email body
        plain_text_body = f"""Hi {display_name},

We received a request to reset your password for your HomeGame.gg account.

Reset your password by visiting:
{reset_url}

---
HomeGame.gg
{request_time_formatted}"""

        # Render HTML email template
        try:
            html_content = render_template(
                'emails/password_reset.html',
                display_name=display_name,
                reset_link=reset_url,
                request_time=request_time_formatted
            )
        except Exception as e:
            logging.warning(f"Failed to render HTML template, falling back to plain text: {str(e)}")
            html_content = None

        # Create SendGrid message with both plain text and HTML
        if html_content:
            message = Mail(
                from_email=From(from_email, "HomeGame.gg Security"),
                to_emails=To(user_email),
                subject=Subject(subject_text),
                plain_text_content=PlainTextContent(plain_text_body),
                html_content=HtmlContent(html_content)
            )
        else:
            # Fallback to plain text only if HTML rendering fails
            message = Mail(
                from_email=From(from_email, "HomeGame.gg Security"),
                to_emails=To(user_email),
                subject=Subject(subject_text),
                plain_text_content=PlainTextContent(plain_text_body)
            )

        # Send email via SendGrid
        sg = SendGridAPIClient(api_key=sendgrid_api_key)
        response = sg.send(message)

        logging.info(f"Password reset email sent to {user_email} (Status: {response.status_code})")
        return True, "Reset email sent successfully"

    except Exception as e:
        logging.error(f"Failed to send password reset email via SendGrid: {str(e)}")
        # Don't reveal whether email exists
        return False, f"Failed to send reset email: {str(e)}"