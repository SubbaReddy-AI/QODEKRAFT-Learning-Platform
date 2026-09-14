import logging
import smtplib
from email.message import EmailMessage
from app.config import settings

logger = logging.getLogger(__name__)

def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send a plain-text email using the configured SMTP account."""
    if not to_email or not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        logger.warning("Reminder email skipped: SMTP credentials are not configured")
        return False
    message = EmailMessage()
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)
    try:
        if settings.MAIL_SSL:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as smtp:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as smtp:
                if settings.MAIL_TLS:
                    smtp.starttls()
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                smtp.send_message(message)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        return False
