import logging

from app.services.channels.base import Message, NotificationChannel

logger = logging.getLogger(__name__)


class LogChannel(NotificationChannel):
    """Logs notifications to stdout. Used when no real channel is configured."""

    async def send(self, message: Message) -> None:
        logger.info(
            "NOTIFICATION (no channel configured)\n  To: %s\n  Subject: %s\n  Body: %s",
            message.to,
            message.subject,
            message.body,
        )
