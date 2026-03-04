"""
Audit trail service.

Records audit entries for all significant actions (lead state changes,
user management, lead creation, etc.).  Background-safe functions open
their own DB session since the request-scoped session is closed by the
time background tasks run.

Failure tracking
----------------
Because record_action() runs inside BackgroundTasks, exceptions never
propagate to the caller.  A lightweight in-memory tracker counts
consecutive failures and escalates to CRITICAL logging when a threshold
is breached, so production alerting can fire.  The tracker also feeds
the /health endpoint.
"""

import logging
import re
import threading
import time
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MAX_SHORT = 50
_MAX_DETAIL = 1000

# ---------------------------------------------------------------------------
# Failure tracker — thread-safe, zero-dependency
# ---------------------------------------------------------------------------
_ALERT_THRESHOLD = 3          # consecutive failures before CRITICAL
_WINDOW_SECONDS = 300         # rolling window for total-failure count


class _AuditFailureTracker:
    """Track audit write failures and escalate on repeated errors."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.consecutive: int = 0
        self.window_failures: int = 0
        self.window_start: float = time.monotonic()
        self.last_error: str | None = None
        self.last_error_ts: float | None = None
        self._alerted: bool = False

    def _maybe_reset_window(self) -> None:
        now = time.monotonic()
        if now - self.window_start >= _WINDOW_SECONDS:
            self.window_failures = 0
            self.window_start = now

    def record_failure(self, error: Exception) -> None:
        with self._lock:
            self._maybe_reset_window()
            self.consecutive += 1
            self.window_failures += 1
            self.last_error = f"{type(error).__name__}: {error}"
            self.last_error_ts = time.time()

            if self.consecutive >= _ALERT_THRESHOLD and not self._alerted:
                logger.critical(
                    "AUDIT SUBSYSTEM DEGRADED — %d consecutive audit write "
                    "failures (%d in last %ds window). Last error: %s",
                    self.consecutive,
                    self.window_failures,
                    _WINDOW_SECONDS,
                    self.last_error,
                )
                self._alerted = True
            elif self._alerted and self.consecutive % _ALERT_THRESHOLD == 0:
                logger.critical(
                    "AUDIT SUBSYSTEM STILL DEGRADED — %d consecutive failures",
                    self.consecutive,
                )

    def record_success(self) -> None:
        with self._lock:
            if self._alerted:
                logger.warning(
                    "Audit subsystem recovered after %d consecutive failures",
                    self.consecutive,
                )
            self.consecutive = 0
            self._alerted = False

    def health(self) -> dict:
        with self._lock:
            self._maybe_reset_window()
            return {
                "healthy": self.consecutive < _ALERT_THRESHOLD,
                "consecutive_failures": self.consecutive,
                "window_failures": self.window_failures,
                "window_seconds": _WINDOW_SECONDS,
                "last_error": self.last_error,
            }


_tracker = _AuditFailureTracker()


def audit_health() -> dict:
    """Return current audit subsystem health (used by /health endpoint)."""
    return _tracker.health()


def _sanitize(value: str | None, *, max_length: int = _MAX_SHORT) -> str | None:
    """Strip control characters and clamp length for audit fields."""
    if value is None:
        return None
    cleaned = _CONTROL_CHARS.sub("", value)
    return cleaned[:max_length]


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
    entity_type = _sanitize(entity_type) or entity_type
    action = _sanitize(action) or action
    user_email = _sanitize(user_email, max_length=255)
    old_state = _sanitize(old_state)
    new_state = _sanitize(new_state)
    detail = _sanitize(detail, max_length=_MAX_DETAIL)

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
            _tracker.record_success()
            logger.info(
                "Audit: %s %s on %s/%s by %s",
                action,
                detail or "",
                entity_type,
                entity_id,
                user_email or "system",
            )
    except Exception as exc:
        _tracker.record_failure(exc)
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
