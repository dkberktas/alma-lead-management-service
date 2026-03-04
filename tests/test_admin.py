import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_create_attorney(client: AsyncClient, admin_token: str):
    resp = await client.post(
        "/api/admin/attorneys",
        json={"email": "new_attorney@test.com", "password": "pass123"},
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
        json={"email": "sneaky@test.com", "password": "pass123"},
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
        json={"email": "deleteme@test.com", "password": "pass123"},
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
async def test_first_user_is_admin(client: AsyncClient):
    resp = await client.post(
        "/api/auth/register",
        json={"email": "first@test.com", "password": "pass123"},
    )
    token = resp.json()["access_token"]

    users_resp = await client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert users_resp.status_code == 200
    users = users_resp.json()
    first_user = next(u for u in users if u["email"] == "first@test.com")
    assert first_user["role"] == "ADMIN"
