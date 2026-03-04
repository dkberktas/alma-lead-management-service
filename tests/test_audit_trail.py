import pytest
from httpx import AsyncClient


def _resume_file():
    return ("resume", ("test.pdf", b"%PDF-fake-content", "application/pdf"))


@pytest.mark.asyncio
async def test_admin_list_audit_logs_empty(client: AsyncClient, admin_token: str):
    resp = await client.get(
        "/api/admin/audit-logs",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["limit"] == 50
    assert body["offset"] == 0


@pytest.mark.asyncio
async def test_attorney_cannot_access_audit_logs(client: AsyncClient, auth_token: str):
    resp = await client.get(
        "/api/admin/audit-logs",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_cannot_access_audit_logs(client: AsyncClient):
    resp = await client.get("/api/admin/audit-logs")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_audit_logs_after_lead_state_change(client: AsyncClient, auth_token: str, admin_token: str):
    """State change should produce an audit entry visible to admins."""
    create_resp = await client.post(
        "/api/leads",
        data={"first_name": "Audit", "last_name": "Test", "email": "audit@test.com"},
        files=[_resume_file()],
    )
    lead_id = create_resp.json()["id"]

    await client.patch(
        f"/api/leads/{lead_id}",
        json={"state": "REACHED_OUT"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    resp = await client.get(
        "/api/admin/audit-logs?entity_type=lead",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    actions = [item["action"] for item in body["items"]]
    assert "state_change" in actions or "lead_created" in actions


@pytest.mark.asyncio
async def test_audit_logs_after_attorney_created(client: AsyncClient, admin_token: str):
    """Creating an attorney should log an audit entry."""
    await client.post(
        "/api/admin/attorneys",
        json={"email": "audited_atty@test.com", "password": "pass1234"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        "/api/admin/audit-logs?entity_type=user",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    actions = [item["action"] for item in body["items"]]
    assert "attorney_created" in actions


@pytest.mark.asyncio
async def test_audit_logs_after_user_deactivated(client: AsyncClient, admin_token: str):
    create_resp = await client.post(
        "/api/admin/attorneys",
        json={"email": "deact_audit@test.com", "password": "pass1234"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    user_id = create_resp.json()["id"]

    await client.patch(
        f"/api/admin/users/{user_id}/deactivate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        "/api/admin/audit-logs?action=user_deactivated",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_audit_logs_pagination(client: AsyncClient, admin_token: str):
    resp = await client.get(
        "/api/admin/audit-logs?limit=2&offset=0",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert len(body["items"]) <= 2


@pytest.mark.asyncio
async def test_audit_log_response_shape(client: AsyncClient, admin_token: str):
    """Verify the response schema of audit log items."""
    await client.post(
        "/api/admin/attorneys",
        json={"email": "shape_test@test.com", "password": "pass1234"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        "/api/admin/audit-logs?limit=1",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    if body["items"]:
        item = body["items"][0]
        assert "id" in item
        assert "entity_type" in item
        assert "entity_id" in item
        assert "action" in item
        assert "created_at" in item
