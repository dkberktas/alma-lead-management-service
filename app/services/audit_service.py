"""
Audit trail service.

Records audit entries for all significant actions (lead state changes,
user management, lead creation, etc.).  Background-safe functions open
their own DB session since the request-scoped session is closed by the
time background tasks run.
"""

import logging
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


async def record_action(
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    action: str,
    user_id: uuid.UUID | None = None,
    user_email: str | None = None,
    old_state: str | None = None,
    new_state: str | None = None,
    detail: str | None = None,
    lead_id: uuid.UUID | None = None,
) -> None:
    """Background-safe: opens its own DB session to persist an audit entry."""
    try:
        async with async_session_factory() as session:
            entry = AuditLog(
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                user_id=user_id,
                user_email=user_email,
                old_state=old_state,
                new_state=new_state,
                detail=detail,
                lead_id=lead_id,
            )
            session.add(entry)
            await session.commit()
            logger.info(
                "Audit: %s %s on %s/%s by %s",
                action,
                detail or "",
                entity_type,
                entity_id,
                user_email or "system",
            )
    except Exception:
        logger.exception(
            "Failed to write audit log for %s/%s", entity_type, entity_id
        )


async def record_state_change(
    *,
    lead_id: uuid.UUID,
    user_id: uuid.UUID,
    user_email: str,
    old_state: str,
    new_state: str,
) -> None:
    """Convenience wrapper kept for backward compatibility."""
    await record_action(
        entity_type="lead",
        entity_id=lead_id,
        action="state_change",
        user_id=user_id,
        user_email=user_email,
        old_state=old_state,
        new_state=new_state,
        lead_id=lead_id,
    )


async def get_lead_audit_logs(
    db: AsyncSession, lead_id: uuid.UUID
) -> list[AuditLog]:
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.lead_id == lead_id)
        .order_by(AuditLog.created_at.desc())
    )
    return list(result.scalars().all())


async def get_all_audit_logs(
    db: AsyncSession,
    *,
    entity_type: str | None = None,
    action: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AuditLog], int]:
    """Return paginated audit logs with optional filters, plus total count."""
    query = select(AuditLog)
    count_query = select(func.count(AuditLog.id))

    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
        count_query = count_query.where(AuditLog.entity_type == entity_type)
    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)

    total = (await db.execute(count_query)).scalar_one()

    query = query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all()), total
