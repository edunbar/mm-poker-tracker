import os
import logging
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From, To, Subject, PlainTextContent

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