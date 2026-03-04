import pytest
from httpx import AsyncClient


def _resume_file():
    return ("resume", ("test.pdf", b"%PDF-fake-content", "application/pdf"))


@pytest.mark.asyncio
async def test_create_lead(client: AsyncClient):
    resp = await client.post(
        "/api/leads",
        data={"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"},
        files=[_resume_file()],
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["first_name"] == "Jane"
    assert data["state"] == "PENDING"
    assert data["resume_path"].endswith(".pdf")


@pytest.mark.asyncio
async def test_create_lead_invalid_file_type(client: AsyncClient):
    resp = await client.post(
        "/api/leads",
        data={"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"},
        files=[("resume", ("test.txt", b"plain text", "text/plain"))],
    )
    assert resp.status_code == 400
    assert "not allowed" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_list_leads_requires_auth(client: AsyncClient):
    resp = await client.get("/api/leads")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_leads(client: AsyncClient, auth_token: str):
    await client.post(
        "/api/leads",
        data={"first_name": "A", "last_name": "B", "email": "a@b.com"},
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
        data={"first_name": "Get", "last_name": "Test", "email": "get@test.com"},
        files=[_resume_file()],
    )
    lead_id = create_resp.json()["id"]
    resp = await client.get(
        f"/api/leads/{lead_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == lead_id


@pytest.mark.asyncio
async def test_update_lead_state(client: AsyncClient, auth_token: str):
    create_resp = await client.post(
        "/api/leads",
        data={"first_name": "State", "last_name": "Test", "email": "state@test.com"},
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
        data={"first_name": "No", "last_name": "Revert", "email": "no@revert.com"},
        files=[_resume_file()],
    )
    lead_id = create_resp.json()["id"]
    headers = {"Authorization": f"Bearer {auth_token}"}
    await client.patch(f"/api/leads/{lead_id}", json={"state": "REACHED_OUT"}, headers=headers)
    resp = await client.patch(f"/api/leads/{lead_id}", json={"state": "PENDING"}, headers=headers)
    assert resp.status_code == 400
