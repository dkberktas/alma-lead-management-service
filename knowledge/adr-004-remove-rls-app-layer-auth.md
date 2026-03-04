# ADR-004: Fix RLS — Defense-in-Depth with Application-Layer Auth

## Status
Accepted (supersedes earlier draft that proposed removing RLS)

## Context
The initial migration (001) defined PostgreSQL Row Level Security policies on `leads` and `users` tables. These policies reference `current_setting('app.current_user_id', true)::uuid` to identify the caller.

Two compounding issues made the policies completely inoperative:

1. **The application never set `app.current_user_id`.** No middleware or session hook called `SET LOCAL app.current_user_id = ...`, so the setting was always NULL.
2. **The `alma` database user is a PostgreSQL superuser.** Docker's `POSTGRES_USER` creates a superuser, which bypasses RLS entirely.

An earlier draft (never merged) proposed removing RLS and relying solely on application-layer auth. Instead, we chose to fix both root causes so RLS provides genuine defense-in-depth.

## Decision
Fix RLS by addressing both root causes:

### 1. Non-superuser app role
Create `alma_app` (non-superuser, `LOGIN`) via a Docker init script (`docker/init-db.sql`). The FastAPI application connects as `alma_app` so RLS policies are enforced. The `alma` superuser is retained exclusively for Alembic migrations.

### 2. Session variable middleware
Add HTTP middleware that decodes the JWT bearer token (if present) and stores the user ID in `request.state.current_user_id`. The `get_db` dependency then executes `SET LOCAL app.current_user_id = ...` on each session, scoped to the current transaction.

### Access model

| Role | DB-level (RLS) | App-level (FastAPI Depends) |
|------|----------------|----------------------------|
| **Public** | INSERT leads only | No auth required on `POST /leads` |
| **Attorney** | SELECT/UPDATE leads; SELECT own user row | `get_current_user` |
| **Admin** | Full access to users table | `require_admin` |

### RLS policies (unchanged from migration 001)

| Table | Policy | Operation | Rule |
|-------|--------|-----------|------|
| leads | leads_active_users_select | SELECT | Active user required |
| leads | leads_active_users_insert | INSERT | Anyone (`WITH CHECK (true)`) |
| leads | leads_active_users_update | UPDATE | Active user required |
| users | users_admin_all | ALL | Admin only |
| users | users_self_select | SELECT | Own row only |

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Remove RLS, app-layer only | Simple; no DB role setup | No DB-level fallback; misleads if RLS code remains |
| Keep RLS as-is (broken) | No code changes | Decorative security; false sense of safety |
| **Fix RLS (this ADR)** | True defense-in-depth; honest security posture | Requires Docker init script + middleware; two DB URLs |

## Consequences
- Two database connection URLs: `DATABASE_URL` (app, non-superuser) and `DATABASE_ADMIN_URL` (Alembic, superuser)
- Docker volume must be recreated (or init script run manually) to create the `alma_app` role on existing setups
- Tests use SQLite (no RLS support) — they validate app-layer auth only; RLS is defense-in-depth active only in PostgreSQL
- `audit_logs` table has no RLS; app-layer auth handles admin-only access. Can be added later if needed
- Public lead submission uses `flush()` + `commit()` instead of `refresh()` since the RLS SELECT policy blocks unauthenticated reads
