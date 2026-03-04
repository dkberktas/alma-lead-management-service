import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


async def _seed_user(
    session: AsyncSession,
    email: str,
    password: str,
    role: UserRole,
) -> None:
    """Create a user if it doesn't already exist. Idempotent."""
    result = await session.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none() is not None:
        logger.info("%s user %s already exists — skipping seed", role.value, email)
        return

    session.add(
        User(
            email=email,
            hashed_password=hash_password(password),
            role=role,
        )
    )
    await session.commit()
    logger.info("Seeded %s user: %s", role.value, email)


async def seed_admin(session: AsyncSession) -> None:
    """Create the initial admin user if ADMIN_EMAIL / ADMIN_PASSWORD are set."""
    if not settings.admin_email or not settings.admin_password:
        logger.debug("ADMIN_EMAIL / ADMIN_PASSWORD not set — skipping admin seed")
        return
    await _seed_user(session, settings.admin_email, settings.admin_password, UserRole.ADMIN)


async def seed_attorney(session: AsyncSession) -> None:
    """Create an attorney user if SEED_ATTORNEY_EMAIL / SEED_ATTORNEY_PASSWORD are set."""
    if not settings.seed_attorney_email or not settings.seed_attorney_password:
        logger.debug("SEED_ATTORNEY_EMAIL / SEED_ATTORNEY_PASSWORD not set — skipping attorney seed")
        return
    await _seed_user(
        session, settings.seed_attorney_email, settings.seed_attorney_password, UserRole.ATTORNEY,
    )
