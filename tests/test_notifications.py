from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.channels.base import Message
from app.services.channels.log import LogChannel
from app.services.channels.resend_email import ResendEmailChannel
from app.services.notification_service import _dispatch, notify_new_lead
from tests.conftest import InMemoryChannel


# ---------------------------------------------------------------------------
# notify_new_lead sends exactly two messages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notify_new_lead_sends_to_all_attorneys(monkeypatch):
    channel = InMemoryChannel()
    monkeypatch.setattr("app.services.notification_service._channels", [channel])

    attorney_emails = ["atty1@alma.com", "atty2@alma.com", "atty3@alma.com"]

    await notify_new_lead(
        prospect_email="jane@example.com",
        first_name="Jane",
        last_name="Doe",
        resume_filename="jane_resume.pdf",
        attorney_emails=attorney_emails,
    )

    # 1 prospect email + 3 attorney emails
    assert len(channel.sent) == 4

    prospect_msg = channel.sent[0]
    assert prospect_msg.to == "jane@example.com"
    assert "received your application" in prospect_msg.subject.lower()
    assert "Jane" in prospect_msg.body

    for i, email in enumerate(attorney_emails):
        attorney_msg = channel.sent[i + 1]
        assert attorney_msg.to == email
        assert "jane@example.com" in attorney_msg.body
        assert "Jane" in attorney_msg.subject
        assert "Doe" in attorney_msg.subject
        assert "jane_resume.pdf" in attorney_msg.body


@pytest.mark.asyncio
async def test_notify_new_lead_falls_back_to_config(monkeypatch):
    """When no attorney_emails are provided, falls back to settings.attorney_email."""
    channel = InMemoryChannel()
    monkeypatch.setattr("app.services.notification_service._channels", [channel])
    monkeypatch.setattr("app.services.notification_service.settings.attorney_email", "fallback@alma.com")

    await notify_new_lead(
        prospect_email="jane@example.com",
        first_name="Jane",
        last_name="Doe",
        resume_filename="jane_resume.pdf",
    )

    assert len(channel.sent) == 2
    assert channel.sent[1].to == "fallback@alma.com"


# ---------------------------------------------------------------------------
# Dispatch continues when a channel fails
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_continues_on_channel_failure():
    failing = AsyncMock(spec=LogChannel)
    failing.send.side_effect = RuntimeError("boom")

    healthy = InMemoryChannel()

    msg = Message(to="a@b.com", subject="Hi", body="Hello")
    await _dispatch([failing, healthy], msg)

    failing.send.assert_awaited_once_with(msg)
    assert len(healthy.sent) == 1


# ---------------------------------------------------------------------------
# LogChannel logs without error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_log_channel_sends_without_error():
    channel = LogChannel()
    msg = Message(to="test@example.com", subject="Test", body="Body")
    await channel.send(msg)


# ---------------------------------------------------------------------------
# ResendEmailChannel calls the Resend API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resend_channel_posts_to_api():
    channel = ResendEmailChannel(api_key="re_test_key", from_address="noreply@alma.com")
    msg = Message(to="user@example.com", subject="Hello", body="World")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = lambda: None
    mock_response.json.return_value = {"id": "email_123"}

    with patch("app.services.channels.resend_email.httpx.AsyncClient") as MockClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client_instance

        await channel.send(msg)

        mock_client_instance.post.assert_awaited_once()
        call_kwargs = mock_client_instance.post.call_args
        assert call_kwargs[0][0] == "https://api.resend.com/emails"
        json_body = call_kwargs[1]["json"]
        assert json_body["from"] == "noreply@alma.com"
        assert json_body["to"] == "user@example.com"
        assert json_body["subject"] == "Hello"
        assert json_body["text"] == "World"
        assert "re_test_key" in call_kwargs[1]["headers"]["Authorization"]
