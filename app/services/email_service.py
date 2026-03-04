import logging
import smtplib
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def _send_smtp(to: str, subject: str, body: str) -> None:
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


def send_email(to: str, subject: str, body: str) -> None:
    if not settings.smtp_host:
        logger.info("EMAIL (dev mode — SMTP not configured)\n  To: %s\n  Subject: %s\n  Body: %s", to, subject, body)
        return

    try:
        _send_smtp(to, subject, body)
    except Exception:
        logger.exception("Failed to send email to %s", to)


def notify_new_lead(prospect_email: str, first_name: str) -> None:
    send_email(
        to=prospect_email,
        subject="We received your application",
        body=f"Hi {first_name},\n\nThank you for submitting your information. Our team will review it and reach out shortly.\n\nBest,\nAlma",
    )

    send_email(
        to=settings.attorney_email,
        subject=f"New lead submitted: {first_name}",
        body=f"A new lead has been submitted by {first_name} ({prospect_email}). Please review it in the dashboard.",
    )
