import uuid
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.requests import Request

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

admin_engine = create_async_engine(settings.database_admin_url, echo=False)
admin_session_factory = async_sessionmaker(admin_engine, expire_on_commit=False)


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        user_id = getattr(request.state, "current_user_id", None)
        if user_id:
            safe_uid = str(uuid.UUID(str(user_id)))
            await session.execute(text(f"SET LOCAL app.current_user_id = '{safe_uid}'"))
        yield session
