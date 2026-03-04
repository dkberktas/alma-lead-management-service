# ADR-001: Database Strategy — PostgreSQL via Docker

## Status
Accepted

## Context
The application needs persistent storage for leads and user accounts. We needed to decide between:
- SQLite for simplicity (zero setup)
- PostgreSQL for production parity

The assignment requires "a storage to persist data" and the code should be "production level."

## Decision
Use **PostgreSQL 16** for both local development and production, running locally via Docker Compose.

Tests use **SQLite in-memory** via `aiosqlite` for speed and zero-dependency CI.

The database URL is config-driven (`DATABASE_URL` env var), so swapping backends is a one-line change.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| SQLite only | Zero setup, single file | No production parity, type leniency hides bugs |
| PostgreSQL without Docker | True parity | Requires local install, harder for reviewers |
| PostgreSQL via Docker | True parity, reproducible, one command | Requires Docker |

## Consequences
- Reviewers need Docker installed to run the app locally (`docker compose up`)
- Tests remain fast (in-memory SQLite) and need no external services
- No risk of SQLite/Postgres behavior differences in development
- Production deployment is straightforward — just point `DATABASE_URL` at the real database
