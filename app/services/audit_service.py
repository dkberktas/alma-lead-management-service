"""
Audit trail service.

Writes audit log entries in the background using its own DB session,
since the request-scoped session is closed by the time background tasks run.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


async def record_state_change(
    *,
    lead_id: uuid.UUID,
    user_id: uuid.UUID,
    user_email: str,
    old_state: str,
    new_state: str,
) -> None:
    """Background-safe: opens its own DB session to persist an audit entry."""
    try:
        async with async_session_factory() as session:
            entry = AuditLog(
                lead_id=lead_id,
                user_id=user_id,
                user_email=user_email,
                action="state_change",
                old_state=old_state,
                new_state=new_state,
            )
            session.add(entry)
            await session.commit()
            logger.info(
                "Audit: user %s changed lead %s from %s to %s",
                user_email,
                lead_id,
                old_state,
                new_state,
            )
    except Exception:
        logger.exception("Failed to write audit log for lead %s", lead_id)


async def get_lead_audit_logs(db: AsyncSession, lead_id: uuid.UUID) -> list[AuditLog]:
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.lead_id == lead_id)
        .order_by(AuditLog.created_at.desc())
    )
    return list(result.scalars().all())
