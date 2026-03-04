"""Tests for audit failure tracking and CRITICAL log escalation."""

import logging
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.services.audit_service import (
    _ALERT_THRESHOLD,
    _AuditFailureTracker,
    _tracker,
    audit_health,
    record_action,
)


class TestAuditFailureTracker:
    def setup_method(self):
        self.tracker = _AuditFailureTracker()

    def test_starts_healthy(self):
        h = self.tracker.health()
        assert h["healthy"] is True
        assert h["consecutive_failures"] == 0
        assert h["window_failures"] == 0

    def test_single_failure_still_healthy(self):
        self.tracker.record_failure(RuntimeError("db gone"))
        h = self.tracker.health()
        assert h["healthy"] is True
        assert h["consecutive_failures"] == 1
        assert h["window_failures"] == 1
        assert "RuntimeError" in h["last_error"]

    def test_threshold_failures_marks_unhealthy(self):
        for i in range(_ALERT_THRESHOLD):
            self.tracker.record_failure(RuntimeError(f"fail {i}"))
        h = self.tracker.health()
        assert h["healthy"] is False
        assert h["consecutive_failures"] == _ALERT_THRESHOLD

    def test_success_resets_consecutive(self):
        for i in range(_ALERT_THRESHOLD):
            self.tracker.record_failure(RuntimeError(f"fail {i}"))
        assert self.tracker.health()["healthy"] is False

        self.tracker.record_success()
        h = self.tracker.health()
        assert h["healthy"] is True
        assert h["consecutive_failures"] == 0

    def test_critical_logged_at_threshold(self, caplog):
        with caplog.at_level(logging.CRITICAL, logger="app.services.audit_service"):
            for i in range(_ALERT_THRESHOLD):
                self.tracker.record_failure(RuntimeError(f"fail {i}"))
        assert any("AUDIT SUBSYSTEM DEGRADED" in r.message for r in caplog.records)

    def test_critical_not_logged_below_threshold(self, caplog):
        with caplog.at_level(logging.CRITICAL, logger="app.services.audit_service"):
            for i in range(_ALERT_THRESHOLD - 1):
                self.tracker.record_failure(RuntimeError(f"fail {i}"))
        assert not any("AUDIT SUBSYSTEM DEGRADED" in r.message for r in caplog.records)

    def test_recovery_logged_as_warning(self, caplog):
        for i in range(_ALERT_THRESHOLD):
            self.tracker.record_failure(RuntimeError(f"fail {i}"))
        with caplog.at_level(logging.WARNING, logger="app.services.audit_service"):
            self.tracker.record_success()
        assert any("recovered" in r.message for r in caplog.records)

    def test_repeated_critical_at_multiples(self, caplog):
        with caplog.at_level(logging.CRITICAL, logger="app.services.audit_service"):
            for i in range(_ALERT_THRESHOLD * 2):
                self.tracker.record_failure(RuntimeError(f"fail {i}"))
        critical_msgs = [r for r in caplog.records if r.levelno == logging.CRITICAL]
        assert len(critical_msgs) == 2


@pytest.mark.asyncio
async def test_record_action_tracks_failure(caplog):
    """record_action() should feed failures into the tracker."""
    _tracker.record_success()  # reset global state

    entity_id = uuid.uuid4()
    with patch(
        "app.services.audit_service.async_session_factory",
        side_effect=RuntimeError("connection refused"),
    ):
        with caplog.at_level(logging.ERROR, logger="app.services.audit_service"):
            for _ in range(_ALERT_THRESHOLD):
                await record_action(
                    entity_type="test",
                    entity_id=entity_id,
                    action="test_action",
                )

    h = audit_health()
    assert h["healthy"] is False
    assert h["consecutive_failures"] >= _ALERT_THRESHOLD

    _tracker.record_success()  # clean up


@pytest.mark.asyncio
async def test_record_action_resets_on_success():
    """Successful audit writes should reset the failure counter."""
    _tracker.record_success()  # reset global state

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.add = lambda _: None
    mock_session.commit = AsyncMock()

    _tracker.record_failure(RuntimeError("earlier failure"))
    assert _tracker.health()["consecutive_failures"] == 1

    with patch(
        "app.services.audit_service.async_session_factory",
        return_value=mock_session,
    ):
        await record_action(
            entity_type="test",
            entity_id=uuid.uuid4(),
            action="test_action",
        )

    assert _tracker.health()["consecutive_failures"] == 0
