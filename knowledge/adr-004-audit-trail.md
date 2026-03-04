# ADR-004: Full Entity Audit Trail

## Status
Accepted

## Context
The original implementation included a narrow audit log that only tracked lead state changes (`PENDING` → `REACHED_OUT`). The `audit_logs` table had non-nullable `lead_id`, `old_state`, and `new_state` columns, making it impossible to record other types of events (user management, logins, lead creation).

Admins needed visibility into **all** significant actions across the system — not just lead state transitions — to support compliance, debugging, and operational oversight.

## Decision
Evolve the `audit_logs` table into a **generic entity audit trail** that records every significant action in the system.

### Data Model

The `AuditLog` model uses two generic columns to identify what was affected:

| Column | Type | Purpose |
|--------|------|---------|
| `entity_type` | `String(50)` | Category of the affected resource (`"lead"`, `"user"`) |
| `entity_id` | `UUID` | Primary key of the affected resource |
| `action` | `String(50)` | What happened (see table below) |
| `user_id` | `UUID` (nullable) | Who performed the action (null for public/system actions) |
| `user_email` | `String` (nullable) | Denormalized email for display without joins |
| `old_state` / `new_state` | `String` (nullable) | Only populated for state-transition actions |
| `detail` | `Text` (nullable) | Human-readable description |
| `lead_id` | `UUID` (nullable) | Kept for backward compat with per-lead audit queries |

The previously non-nullable columns (`lead_id`, `user_id`, `old_state`, `new_state`) are now nullable. Alembic migration `003` handles the schema change and backfills existing rows with `entity_type='lead'`.

### Tracked Actions

| Action | Entity Type | Trigger |
|--------|------------|---------|
| `lead_created` | `lead` | Public lead submission |
| `state_change` | `lead` | Attorney marks lead as REACHED_OUT |
| `user_registered` | `user` | New user registration |
| `user_login` | `user` | Successful login |
| `attorney_created` | `user` | Admin creates attorney account |
| `user_deactivated` | `user` | Admin deactivates a user |
| `user_reactivated` | `user` | Admin reactivates a user |
| `user_deleted` | `user` | Admin permanently deletes a user |

### Write Path

All audit entries are written via **background tasks** (`BackgroundTasks.add_task`) calling `audit_service.record_action()`. This function opens its own database session (`async_session_factory()`) because the request-scoped session is closed by the time background tasks execute. Failures are logged but never block the primary request — audit writes are best-effort.

### Read Path

- **Per-lead audit log**: `GET /api/leads/{id}/audit-log` — available to all authenticated users, queries by `lead_id`.
- **Global audit trail**: `GET /api/admin/audit-logs` — admin-only, supports query params:
  - `entity_type` — filter by `"lead"` or `"user"`
  - `action` — filter by specific action
  - `limit` / `offset` — pagination (default 50, max 200)
  - Returns `{ items, total, limit, offset }` for frontend pagination.

### Frontend

Admin users see an "Audit Trail" link in the navigation bar. The page (`/audit`) shows a paginated table with:
- Timestamp, color-coded action badge, entity type with icon, acting user, and detail/state change
- Filter tabs: All / Leads / Users
- Previous/Next pagination

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Separate tables per entity type | Strong typing, no nullable columns | More tables, more queries, harder to get a unified timeline |
| Event sourcing | Complete history, replayable | Massive complexity increase for a CRUD app |
| Third-party audit service (e.g., Audit.log) | Managed, tamper-proof | External dependency, cost, network latency |
| Keep narrow lead-only audit | No migration needed | Admin has no visibility into user management actions |

## Consequences
- The `audit_logs` table grows with every tracked action. For high-traffic deployments, consider adding a retention policy or archiving old entries.
- `user_email` is denormalized into audit rows so the trail remains readable even after a user is deleted.
- Adding new audited actions is a one-line `background_tasks.add_task(audit_service.record_action, ...)` call in any route handler.
- The background-task write pattern means audit entries may appear with a slight delay after the action completes. They will also be lost if the process crashes between the response and the background task execution.
