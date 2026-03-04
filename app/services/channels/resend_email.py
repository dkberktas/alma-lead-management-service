import logging

import httpx

from app.services.channels.base import Message, NotificationChannel

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


class ResendEmailChannel(NotificationChannel):
    """Sends email via the Resend API (https://resend.com)."""

    def __init__(self, api_key: str, from_address: str) -> None:
        self._api_key = api_key
        self._from_address = from_address

    async def send(self, message: Message) -> None:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                RESEND_API_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "from": self._from_address,
                    "to": message.to,
                    "subject": message.subject,
                    "text": message.body,
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            logger.info("Email sent via Resend to %s (id=%s)", message.to, resp.json().get("id"))
