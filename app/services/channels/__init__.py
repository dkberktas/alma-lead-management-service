"""
Pluggable notification channels.

Priority: Resend > SMTP > log-only fallback.
Set RESEND_API_KEY *or* SMTP_HOST (+ credentials) to enable email delivery.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.channels.base import Message, NotificationChannel
from app.services.channels.log import LogChannel
from app.services.channels.resend_email import ResendEmailChannel
from app.services.channels.smtp_email import SmtpEmailChannel

if TYPE_CHECKING:
    from app.core.config import Settings

__all__ = ["Message", "NotificationChannel", "get_channels"]


def get_channels(settings: Settings) -> list[NotificationChannel]:
    channels: list[NotificationChannel] = []

    if settings.resend_api_key:
        channels.append(
            ResendEmailChannel(
                api_key=settings.resend_api_key,
                from_address=settings.email_from,
            )
        )
    elif settings.smtp_host:
        channels.append(
            SmtpEmailChannel(
                host=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user,
                password=settings.smtp_password,
                from_address=settings.email_from,
                use_tls=settings.smtp_use_tls,
            )
        )

    if not channels:
        channels.append(LogChannel())

    return channels
