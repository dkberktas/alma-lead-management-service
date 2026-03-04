import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


async def seed_admin(session: AsyncSession) -> None:
    """Create the initial admin user if ADMIN_EMAIL and ADMIN_PASSWORD are set.

    Idempotent: skips silently when the env vars are empty or when an account
    with that email already exists.
    """
    if not settings.admin_email or not settings.admin_password:
        logger.debug("ADMIN_EMAIL / ADMIN_PASSWORD not set — skipping admin seed")
        return

    result = await session.execute(
        select(User).where(User.email == settings.admin_email)
    )
    if result.scalar_one_or_none() is not None:
        logger.info("Admin user %s already exists — skipping seed", settings.admin_email)
        return

    user = User(
        email=settings.admin_email,
        hashed_password=hash_password(settings.admin_password),
        role=UserRole.ADMIN,
    )
    session.add(user)
    await session.commit()
    logger.info("Seeded admin user: %s", settings.admin_email)
