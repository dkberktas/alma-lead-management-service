from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import get_db
from app.main import app
from app.models.base import Base
from app.services import file_service
from app.services.storage import FileInfo

TEST_DB_URL = "sqlite+aiosqlite://"


class InMemoryStorageBackend:
    """Test-only backend that stores files in a dict."""

    def __init__(self) -> None:
        self._files: dict[str, bytes] = {}

    async def save(self, data: bytes, key: str) -> str:
        self._files[key] = data
        return key

    def url(self, key: str) -> str:
        return f"mem://{key}"

    async def list_files(self) -> list[FileInfo]:
        return [
            FileInfo(key=k, size_bytes=len(v), last_modified=datetime.now(timezone.utc))
            for k, v in self._files.items()
        ]


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    test_engine = create_async_engine(TEST_DB_URL, echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with test_session_factory() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    file_service._backend = InMemoryStorageBackend()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    file_service._backend = None


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient) -> str:
    """First registered user becomes admin."""
    resp = await client.post(
        "/api/auth/register",
        json={"email": "admin@test.com", "password": "adminpass123"},
    )
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def auth_token(client: AsyncClient, admin_token: str) -> str:
    """Second registered user is an attorney."""
    resp = await client.post(
        "/api/auth/register",
        json={"email": "attorney@test.com", "password": "testpass123"},
    )
    return resp.json()["access_token"]
