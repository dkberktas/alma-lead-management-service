import pytest
from httpx import AsyncClient


def _resume_file():
    return ("resume", ("test.pdf", b"%PDF-fake-content", "application/pdf"))


def _valid_lead_data(**overrides):
    data = {"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"}
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# Happy-path creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_lead(client: AsyncClient):
    resp = await client.post(
        "/api/leads",
        data=_valid_lead_data(),
        files=[_resume_file()],
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["first_name"] == "Jane"
    assert data["last_name"] == "Doe"
    assert data["email"] == "jane@example.com"
    assert data["state"] == "PENDING"
    assert data["resume_path"].endswith(".pdf")


@pytest.mark.asyncio
async def test_create_lead_strips_whitespace(client: AsyncClient):
    resp = await client.post(
        "/api/leads",
        data=_valid_lead_data(first_name="  Alice  ", last_name="  Smith  "),
        files=[_resume_file()],
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["first_name"] == "Alice"
    assert data["last_name"] == "Smith"


# ---------------------------------------------------------------------------
# Email validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_email", [
    "not-an-email",
    "missing-at.com",
    "@no-local-part.com",
    "spaces in@email.com",
    "user@",
    "",
    "user@.com",
    "user@com",
])
async def test_create_lead_rejects_invalid_email(client: AsyncClient, bad_email: str):
    resp = await client.post(
        "/api/leads",
        data=_valid_lead_data(email=bad_email),
        files=[_resume_file()],
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("good_email", [
    "user@example.com",
    "first.last@domain.org",
    "user+tag@example.com",
    "name@sub.domain.co.uk",
])
async def test_create_lead_accepts_valid_email(client: AsyncClient, good_email: str):
    resp = await client.post(
        "/api/leads",
        data=_valid_lead_data(email=good_email),
        files=[_resume_file()],
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == good_email


# ---------------------------------------------------------------------------
# Required fields — missing individual fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_lead_missing_first_name(client: AsyncClient):
    resp = await client.post(
        "/api/leads",
        data={"last_name": "Doe", "email": "a@b.com"},
        files=[_resume_file()],
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_lead_missing_last_name(client: AsyncClient):
    resp = await client.post(
        "/api/leads",
        data={"first_name": "Jane", "email": "a@b.com"},
        files=[_resume_file()],
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_lead_missing_email(client: AsyncClient):
    resp = await client.post(
        "/api/leads",
        data={"first_name": "Jane", "last_name": "Doe"},
        files=[_resume_file()],
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_lead_missing_resume(client: AsyncClient):
    resp = await client.post(
        "/api/leads",
        data=_valid_lead_data(),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_lead_no_fields_at_all(client: AsyncClient):
    resp = await client.post("/api/leads")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Name length validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_lead_first_name_too_long(client: AsyncClient):
    resp = await client.post(
        "/api/leads",
        data=_valid_lead_data(first_name="A" * 101),
        files=[_resume_file()],
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_lead_last_name_too_long(client: AsyncClient):
    resp = await client.post(
        "/api/leads",
        data=_valid_lead_data(last_name="B" * 101),
        files=[_resume_file()],
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_lead_name_at_max_length(client: AsyncClient):
    resp = await client.post(
        "/api/leads",
        data=_valid_lead_data(first_name="A" * 100, last_name="B" * 100),
        files=[_resume_file()],
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_create_lead_whitespace_only_first_name(client: AsyncClient):
    resp = await client.post(
        "/api/leads",
        data=_valid_lead_data(first_name="   "),
        files=[_resume_file()],
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_lead_whitespace_only_last_name(client: AsyncClient):
    resp = await client.post(
        "/api/leads",
        data=_valid_lead_data(last_name="   "),
        files=[_resume_file()],
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# File upload validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_lead_invalid_file_type(client: AsyncClient):
    resp = await client.post(
        "/api/leads",
        data=_valid_lead_data(),
        files=[("resume", ("test.txt", b"plain text", "text/plain"))],
    )
    assert resp.status_code == 400
    assert "not allowed" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Auth-gated endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_leads_requires_auth(client: AsyncClient):
    resp = await client.get("/api/leads")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_leads(client: AsyncClient, auth_token: str):
    await client.post(
        "/api/leads",
        data=_valid_lead_data(email="list@test.com"),
        files=[_resume_file()],
    )
    resp = await client.get(
        "/api/leads",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_get_lead(client: AsyncClient, auth_token: str):
    create_resp = await client.post(
        "/api/leads",
        data=_valid_lead_data(email="get@test.com"),
        files=[_resume_file()],
    )
    lead_id = create_resp.json()["id"]
    resp = await client.get(
        f"/api/leads/{lead_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == lead_id


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_lead_state(client: AsyncClient, auth_token: str):
    create_resp = await client.post(
        "/api/leads",
        data=_valid_lead_data(email="state@test.com"),
        files=[_resume_file()],
    )
    lead_id = create_resp.json()["id"]
    resp = await client.patch(
        f"/api/leads/{lead_id}",
        json={"state": "REACHED_OUT"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "REACHED_OUT"


@pytest.mark.asyncio
async def test_cannot_revert_state(client: AsyncClient, auth_token: str):
    create_resp = await client.post(
        "/api/leads",
        data=_valid_lead_data(email="no@revert.com"),
        files=[_resume_file()],
    )
    lead_id = create_resp.json()["id"]
    headers = {"Authorization": f"Bearer {auth_token}"}
    await client.patch(f"/api/leads/{lead_id}", json={"state": "REACHED_OUT"}, headers=headers)
    resp = await client.patch(f"/api/leads/{lead_id}", json={"state": "PENDING"}, headers=headers)
    assert resp.status_code == 400
