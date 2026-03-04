import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_create_attorney(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/admin/attorneys",
        json={"email": "new_attorney@test.com", "password": "pass1234"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new_attorney@test.com"
    assert data["role"] == "ATTORNEY"


@pytest.mark.asyncio
async def test_attorney_cannot_create_attorney(client: AsyncClient, auth_token: str):
    resp = await client.post(
        "/api/admin/attorneys",
        json={"email": "sneaky@test.com", "password": "pass1234"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 403
    assert "Admin access required" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_admin_list_users(client: AsyncClient, admin_token: str):
    resp = await client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) >= 1
    roles = {u["role"] for u in users}
    assert "ADMIN" in roles


@pytest.mark.asyncio
async def test_attorney_cannot_list_users(client: AsyncClient, auth_token: str):
    resp = await client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_delete_attorney(client: AsyncClient, admin_token: str):
    create_resp = await client.post(
        "/api/admin/attorneys",
        json={"email": "deleteme@test.com", "password": "pass1234"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    user_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 204

    get_resp = await client.get(
        f"/api/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_cannot_delete_self(client: AsyncClient, admin_token: str):
    users_resp = await client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    admin_user = next(u for u in users_resp.json() if u["role"] == "ADMIN")

    resp = await client.delete(
        f"/api/admin/users/{admin_user['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400
    assert "Cannot delete your own account" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_attorney_cannot_delete_user(client: AsyncClient, auth_token: str, admin_token: str):
    users_resp = await client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    admin_user = next(u for u in users_resp.json() if u["role"] == "ADMIN")

    resp = await client.delete(
        f"/api/admin/users/{admin_user['id']}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_cannot_access_admin(client: AsyncClient):
    resp = await client.get("/api/admin/users")
    assert resp.status_code == 403

    resp = await client.post(
        "/api/admin/attorneys",
        json={"email": "x@test.com", "password": "p"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_list_files_empty(client: AsyncClient, admin_token: str):
    resp = await client.get(
        "/api/admin/files",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_admin_list_files_after_upload(client: AsyncClient, admin_token: str):
    await client.post(
        "/api/leads",
        data={"first_name": "File", "last_name": "Test", "email": "file@test.com"},
        files=[("resume", ("test.pdf", b"%PDF-fake-content", "application/pdf"))],
    )
    resp = await client.get(
        "/api/admin/files",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    files = resp.json()
    assert len(files) >= 1
    f = files[0]
    assert "key" in f
    assert f["size_bytes"] > 0
    assert "last_modified" in f


@pytest.mark.asyncio
async def test_attorney_cannot_list_files(client: AsyncClient, auth_token: str):
    resp = await client.get(
        "/api/admin/files",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_deactivate_attorney(client: AsyncClient, admin_token: str):
    create_resp = await client.post(
        "/api/admin/attorneys",
        json={"email": "deactivate_me@test.com", "password": "pass1234"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    user_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/admin/users/{user_id}/deactivate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_active"] is False

    get_resp = await client.get(
        f"/api/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_deactivated_attorney_cannot_login(client: AsyncClient, admin_token: str):
    await client.post(
        "/api/admin/attorneys",
        json={"email": "blocked@test.com", "password": "pass1234"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    login_resp = await client.post(
        "/api/auth/login",
        json={"email": "blocked@test.com", "password": "pass1234"},
    )
    assert login_resp.status_code == 200

    users_resp = await client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    blocked_user = next(u for u in users_resp.json() if u["email"] == "blocked@test.com")

    await client.patch(
        f"/api/admin/users/{blocked_user['id']}/deactivate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    login_resp = await client.post(
        "/api/auth/login",
        json={"email": "blocked@test.com", "password": "pass1234"},
    )
    assert login_resp.status_code == 403
    assert "deactivated" in login_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_reactivate_attorney(client: AsyncClient, admin_token: str):
    create_resp = await client.post(
        "/api/admin/attorneys",
        json={"email": "reactivate_me@test.com", "password": "pass1234"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    user_id = create_resp.json()["id"]

    await client.patch(
        f"/api/admin/users/{user_id}/deactivate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.patch(
        f"/api/admin/users/{user_id}/reactivate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True

    login_resp = await client.post(
        "/api/auth/login",
        json={"email": "reactivate_me@test.com", "password": "pass1234"},
    )
    assert login_resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_cannot_deactivate_self(client: AsyncClient, admin_token: str):
    users_resp = await client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    admin_user = next(u for u in users_resp.json() if u["role"] == "ADMIN")

    resp = await client.patch(
        f"/api/admin/users/{admin_user['id']}/deactivate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400
    assert "Cannot deactivate your own account" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_deactivated_user_token_rejected(client: AsyncClient, admin_token: str):
    create_resp = await client.post(
        "/api/admin/attorneys",
        json={"email": "token_test@test.com", "password": "pass1234"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    user_id = create_resp.json()["id"]

    login_resp = await client.post(
        "/api/auth/login",
        json={"email": "token_test@test.com", "password": "pass1234"},
    )
    attorney_token = login_resp.json()["access_token"]

    leads_resp = await client.get(
        "/api/leads",
        headers={"Authorization": f"Bearer {attorney_token}"},
    )
    assert leads_resp.status_code == 200

    await client.patch(
        f"/api/admin/users/{user_id}/deactivate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    leads_resp = await client.get(
        "/api/leads",
        headers={"Authorization": f"Bearer {attorney_token}"},
    )
    assert leads_resp.status_code == 403
    assert "deactivated" in leads_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_seeded_via_fixture(client: AsyncClient, admin_token: str):
    """Admin is created via DB seed/fixture, not open registration."""
    resp = await client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    users = resp.json()
    admin = next(u for u in users if u["email"] == "admin@test.com")
    assert admin["role"] == "ADMIN"
