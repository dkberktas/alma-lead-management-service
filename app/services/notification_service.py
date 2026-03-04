"""
Business logic for lead notifications.

Dispatches messages to all configured notification channels.
"""

import logging

from app.core.config import settings
from app.services.channels import Message, NotificationChannel, get_channels

logger = logging.getLogger(__name__)

_channels: list[NotificationChannel] | None = None


def _get_channels() -> list[NotificationChannel]:
    global _channels
    if _channels is None:
        _channels = get_channels(settings)
    return _channels


async def _dispatch(channels: list[NotificationChannel], message: Message) -> None:
    for channel in channels:
        try:
            await channel.send(message)
        except Exception:
            logger.exception(
                "Channel %s failed to send to %s",
                type(channel).__name__,
                message.to,
            )


async def notify_new_lead(
    prospect_email: str,
    first_name: str,
    last_name: str,
    resume_filename: str,
    attorney_emails: list[str] | None = None,
) -> None:
    channels = _get_channels()

    await _dispatch(
        channels,
        Message(
            to=prospect_email,
            subject="We received your application",
            body=(
                f"Hi {first_name},\n\n"
                "Thank you for submitting your information. "
                "Our team will review it and reach out shortly.\n\n"
                "Best,\nAlma"
            ),
        ),
    )

    recipients = attorney_emails if attorney_emails else [settings.attorney_email]
    for email in recipients:
        await _dispatch(
            channels,
            Message(
                to=email,
                subject=f"New lead submitted: {first_name} {last_name}",
                body=(
                    f"A new lead has been submitted.\n\n"
                    f"  Name:   {first_name} {last_name}\n"
                    f"  Email:  {prospect_email}\n"
                    f"  Resume: {resume_filename}\n\n"
                    "Please review it in the dashboard."
                ),
            ),
        )
