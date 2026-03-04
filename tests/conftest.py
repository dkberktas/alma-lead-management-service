from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.api.routes import auth as auth_routes
from app.api.routes import leads as leads_routes
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.main import app
from app.models.base import Base
from app.services import audit_service, file_service, notification_service
from app.services.channels.base import Message, NotificationChannel
from app.services.storage import FileInfo

TEST_DB_URL = "sqlite+aiosqlite://"


class InMemoryChannel(NotificationChannel):
    """Test-only channel that collects sent messages in a list."""

    def __init__(self) -> None:
        self.sent: list[Message] = []

    async def send(self, message: Message) -> None:
        self.sent.append(message)


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


@pytest_asyncio.fixture(autouse=True)
async def _reset_rate_limiter():
    limiter.reset()
    yield
    limiter.reset()


@pytest_asyncio.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with test_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, test_engine: AsyncEngine) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db():
        yield db_session

    test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    app.dependency_overrides[get_db] = _override_get_db
    file_service._backend = InMemoryStorageBackend()
    notification_service._channels = [InMemoryChannel()]

    _original_factory = audit_service.async_session_factory
    audit_service.async_session_factory = test_session_factory

    _original_auth_admin = auth_routes.admin_session_factory
    auth_routes.admin_session_factory = test_session_factory
    _original_leads_admin = leads_routes.admin_session_factory
    leads_routes.admin_session_factory = test_session_factory

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    file_service._backend = None
    notification_service._channels = None
    audit_service.async_session_factory = _original_factory
    auth_routes.admin_session_factory = _original_auth_admin
    leads_routes.admin_session_factory = _original_leads_admin


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient, db_session: AsyncSession) -> str:
    """Create an admin user directly and return a JWT."""
    from app.core.security import create_access_token
    from app.models.user import UserRole
    from app.services import auth_service

    user = await auth_service.register_user(
        db_session, email="admin@test.com", password="adminpass123", role=UserRole.ADMIN
    )
    return create_access_token(subject=str(user.id), role=user.role.value)


@pytest_asyncio.fixture
async def auth_token(client: AsyncClient, db_session: AsyncSession, admin_token: str) -> str:
    """Create an attorney user directly and return a JWT."""
    from app.core.security import create_access_token
    from app.models.user import UserRole
    from app.services import auth_service

    user = await auth_service.register_user(
        db_session, email="attorney@test.com", password="testpass123", role=UserRole.ATTORNEY
    )
    return create_access_token(subject=str(user.id), role=user.role.value)
