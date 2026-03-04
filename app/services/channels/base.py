from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Message:
    to: str
    subject: str
    body: str


class NotificationChannel(ABC):
    """Interface that all notification channels must implement."""

    @abstractmethod
    async def send(self, message: Message) -> None:
        """Deliver *message* through this channel."""
