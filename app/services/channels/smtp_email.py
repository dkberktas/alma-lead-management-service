import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.services.channels.base import Message, NotificationChannel

logger = logging.getLogger(__name__)


class SmtpEmailChannel(NotificationChannel):
    """Sends email via SMTP (works with Gmail, Outlook, or any SMTP relay)."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        from_address: str,
        use_tls: bool = True,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from_address = from_address
        self._use_tls = use_tls

    def _send_sync(self, message: Message) -> None:
        msg = EmailMessage()
        msg["From"] = self._from_address
        msg["To"] = message.to
        msg["Subject"] = message.subject
        msg.set_content(message.body)

        with smtplib.SMTP(self._host, self._port) as server:
            if self._use_tls:
                server.starttls()
            server.login(self._username, self._password)
            server.send_message(msg)

    async def send(self, message: Message) -> None:
        await asyncio.to_thread(self._send_sync, message)
        logger.info("Email sent via SMTP to %s", message.to)
