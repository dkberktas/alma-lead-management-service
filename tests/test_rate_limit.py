import pytest
from httpx import AsyncClient


def _resume_file():
    return ("resume", ("test.pdf", b"%PDF-fake-content", "application/pdf"))


def _valid_lead_data(**overrides):
    data = {"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"}
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_requests_within_limit_succeed(client: AsyncClient):
    resp = await client.post(
        "/api/leads",
        data=_valid_lead_data(),
        files=[_resume_file()],
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_exceeding_rate_limit_returns_429(client: AsyncClient):
    """Default limit is 5/minute. The 6th request should be rejected."""
    for i in range(5):
        resp = await client.post(
            "/api/leads",
            data=_valid_lead_data(email=f"user{i}@rate.com"),
            files=[_resume_file()],
        )
        assert resp.status_code == 201

    resp = await client.post(
        "/api/leads",
        data=_valid_lead_data(email="overflow@rate.com"),
        files=[_resume_file()],
    )
    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_response_has_retry_after(client: AsyncClient):
    """The 429 response must include a Retry-After header."""
    for i in range(5):
        await client.post(
            "/api/leads",
            data=_valid_lead_data(email=f"fill{i}@rate.com"),
            files=[_resume_file()],
        )

    resp = await client.post(
        "/api/leads",
        data=_valid_lead_data(email="retry@rate.com"),
        files=[_resume_file()],
    )
    assert resp.status_code == 429
    assert "retry-after" in resp.headers
