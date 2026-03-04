import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import auth_service


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession):
    await auth_service.register_user(db_session, email="login@test.com", password="secret123")
    resp = await client.post(
        "/api/auth/login",
        json={"email": "login@test.com", "password": "secret123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, db_session: AsyncSession):
    await auth_service.register_user(db_session, email="wrong@test.com", password="correct1")
    resp = await client.post(
        "/api/auth/login",
        json={"email": "wrong@test.com", "password": "incorrect"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post(
        "/api/auth/login",
        json={"email": "ghost@test.com", "password": "anything"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_register_endpoint_removed(client: AsyncClient):
    resp = await client.post(
        "/api/auth/register",
        json={"email": "new@test.com", "password": "secret123"},
    )
    assert resp.status_code == 404
