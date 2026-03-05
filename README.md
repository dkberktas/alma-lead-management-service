# Alma Lead Management Service

A FastAPI application for managing prospect leads. Prospects submit their information and resume through a public API. Attorneys review leads through authenticated internal endpoints.

## Prerequisites

- **Docker** and **Docker Compose** (for the recommended setup)
- **Python 3.11+** (only if running without Docker)

## Quick Start (Docker)

```bash
# 1. Clone the repo
git clone https://github.com/<your-username>/alma_lead_management_service.git
cd alma_lead_management_service

# 2. Create your .env file
cp .env.example .env

# 3. Start PostgreSQL + the API
docker compose up --build

# 4. Verify it's running
curl http://localhost:8000/health
# → {"status":"ok"}
```

The API is now available at **http://localhost:8000**.

> **Explore the API:** Open [Swagger UI](http://localhost:8000/docs) for interactive docs, import the [Postman collection](postman/Alma_Lead_Management.postman_collection.json) for pre-built requests, or run the [Admin UI](#admin-frontend) (`cd frontend/admin && npm run dev`) to manage leads from a browser.

### Stopping

```bash
docker compose down      # stop containers, keep database data
docker compose down -v   # stop containers AND wipe database
```

## Running Without Docker

If you prefer to run outside Docker, you'll need a PostgreSQL instance running locally.

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create your .env (set DATABASE_URL to point at your local Postgres)
cp .env.example .env
# Edit .env: change @db:5432 to @localhost:5432

# 4. Run the server
uvicorn app.main:app --reload --port 8000
```

## Database Migrations

Schema changes are managed with [Alembic](https://alembic.sqlalchemy.org/). The Docker container runs `alembic upgrade head` automatically on startup.

### Creating a new migration

After modifying a SQLAlchemy model, generate a migration:

```bash
# Inside the Docker container
docker compose exec app alembic revision --autogenerate -m "describe the change"

# Or from the host (override DATABASE_URL to use localhost)
DATABASE_URL=postgresql+asyncpg://alma:alma_dev_password@localhost:5432/alma_leads \
  alembic revision --autogenerate -m "describe the change"
```

Review the generated file in `alembic/versions/`, then apply:

```bash
docker compose exec app alembic upgrade head
```

### Useful Alembic commands

```bash
alembic current          # show current revision
alembic history          # list all migrations
alembic upgrade head     # apply all pending migrations
alembic downgrade -1     # roll back the last migration
```

> **Note:** Tests use an in-memory SQLite database with `create_all()` and are unaffected by Alembic migrations.

## Running Tests

Tests use an in-memory SQLite database — no Docker or Postgres needed.

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

## Smoke Test

An end-to-end script that creates attorneys, submits leads, and verifies the full workflow against a running instance:

```bash
./scripts/smoke_test.sh                          # defaults to localhost:8000
./scripts/smoke_test.sh http://some-host:8000    # custom target
```

> **Note:** The smoke test creates data in the database. Run `docker compose down -v && docker compose up -d` for a clean slate before re-running.

## API Endpoints

### Public

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/leads` | Submit a new lead (multipart form with resume file) |
| `GET` | `/health` | Health check |

### Auth

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/login` | Login and receive a JWT |

### Internal — Attorney or Admin (requires `Authorization: Bearer <token>`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/leads` | List all leads (supports `state`, `limit`, `offset` query params) |
| `GET` | `/api/leads/{id}` | Get a single lead |
| `PATCH` | `/api/leads/{id}` | Update lead state (`PENDING` → `REACHED_OUT`) |
| `GET` | `/api/leads/{id}/resume-url` | Get a short-lived download URL for the lead's resume |

### Admin Only (requires admin JWT)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/admin/attorneys` | Create a new attorney account |
| `GET` | `/api/admin/users` | List all users (admins + attorneys) |
| `GET` | `/api/admin/users/{id}` | Get a single user |
| `PATCH` | `/api/admin/users/{id}/deactivate` | Soft-deactivate a user (disables login) |
| `PATCH` | `/api/admin/users/{id}/reactivate` | Re-enable a deactivated user |
| `DELETE` | `/api/admin/users/{id}` | Permanently delete a user (cannot delete self) |
| `GET` | `/api/admin/files` | List all uploaded files (from S3) |
| `GET` | `/api/admin/audit-logs` | List audit trail (supports `entity_type`, `action`, `limit`, `offset`) |
| `GET` | `/api/leads/{id}/audit-log` | Get audit log for a specific lead |

## API Usage Examples

### Submit a lead (public)

```bash
curl -X POST http://localhost:8000/api/leads \
  -F "first_name=Jane" \
  -F "last_name=Doe" \
  -F "email=jane@example.com" \
  -F "resume=@resume.pdf;type=application/pdf"
```

### Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@alma.com","password":"securepass"}'
# → {"access_token":"eyJ...","token_type":"bearer"}
```

### Create an attorney (admin only)

```bash
curl -X POST http://localhost:8000/api/admin/attorneys \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"email":"attorney@alma.com","password":"securepass"}'
```

### List leads (authenticated)

```bash
curl http://localhost:8000/api/leads \
  -H "Authorization: Bearer <token>"
```

### Get a resume download URL (authenticated)

```bash
curl http://localhost:8000/api/leads/<lead-id>/resume-url \
  -H "Authorization: Bearer <token>"
# → {"url":"https://s3.amazonaws.com/...?X-Amz-Signature=..."}
```

The returned URL is a presigned S3 URL valid for 5 minutes. Open it in a browser or use it in an `<iframe>` / `<a href>` to download the file.

### Mark a lead as reached out

```bash
curl -X PATCH http://localhost:8000/api/leads/<lead-id> \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"state":"REACHED_OUT"}'
```

## Project Structure

```
alembic/
├── env.py             # Async migration environment
├── script.py.mako     # Migration template
└── versions/          # Migration scripts (001_initial_schema.py, ...)
app/
├── api/routes/        # Route handlers (thin controllers)
│   ├── admin.py       # Admin-only user management
│   ├── auth.py        # Login
│   └── leads.py       # Lead CRUD
├── core/              # Config, security, dependencies
│   ├── config.py      # Environment-driven settings
│   ├── dependencies.py # Auth dependencies (get_current_user, require_admin)
│   ├── rate_limit.py  # slowapi rate limiter instance
│   └── security.py    # JWT + bcrypt utilities
├── db/
│   ├── seed.py        # Admin user bootstrap on startup
│   └── session.py     # Async SQLAlchemy engine + session
├── models/            # SQLAlchemy ORM models
│   ├── audit_log.py   # AuditLog (entity tracking, state changes)
│   ├── lead.py        # Lead (id, name, email, resume, state)
│   └── user.py        # User (admin/attorney with role enum)
├── schemas/           # Pydantic request/response models
│   ├── auth.py
│   └── lead.py
├── services/          # Business logic layer
│   ├── audit_service.py   # Audit trail recording and querying
│   ├── auth_service.py
│   ├── channels/      # Pluggable notification channels (Resend, SMTP, log)
│   ├── file_service.py
│   ├── lead_service.py
│   ├── notification_service.py
│   └── storage.py     # S3 storage backend
└── main.py            # App entry point
tests/                 # pytest test suite
scripts/               # Utility scripts (smoke test)
knowledge/             # Project context, ADRs, open questions
frontend/
└── admin/             # Attorney admin UI (React + Vite)
```

## Configuration

All settings are loaded from environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Environment name (`development`, `staging`, `production`) |
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async database connection string |
| `SECRET_KEY` | — | JWT signing key (change in production!) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT token lifetime |
| `RESEND_API_KEY` | *(empty)* | [Resend](https://resend.com) API key (takes priority over SMTP) |
| `SMTP_HOST` | *(empty)* | SMTP server (e.g. `smtp.gmail.com`). Falls back to log-only if empty |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` / `SMTP_PASSWORD` | — | SMTP credentials (use App Password for Gmail) |
| `SMTP_USE_TLS` | `true` | Enable STARTTLS |
| `EMAIL_FROM` | `noreply@alma.com` | Sender address |
| `ATTORNEY_EMAIL` | `attorney@alma.com` | Notification recipient for new leads |
| `MAX_UPLOAD_SIZE_MB` | `10` | Max resume file size |
| `RATE_LIMIT_PER_MINUTE` | `5` | Max lead submissions per IP per minute |
| `RATE_LIMIT_PER_HOUR` | `20` | Max lead submissions per IP per hour |
| `S3_BUCKET` | — | S3 bucket name (required) |
| `S3_PREFIX` | `resumes` | S3 key prefix for uploaded files |
| `S3_REGION` | *(empty)* | AWS region (e.g., `us-east-1`) |
| `S3_ENDPOINT_URL` | *(empty)* | Custom S3 endpoint (for MinIO / LocalStack) |
| `AWS_ACCESS_KEY_ID` | *(boto3 chain)* | AWS access key — see [File Storage](#file-storage) |
| `AWS_SECRET_ACCESS_KEY` | *(boto3 chain)* | AWS secret key — see [File Storage](#file-storage) |
| `ADMIN_EMAIL` | *(empty)* | Seed admin email (see [Admin Bootstrap](#admin-bootstrap)) |
| `ADMIN_PASSWORD` | *(empty)* | Seed admin password |

## Rate Limiting

The public lead submission endpoint (`POST /api/leads`) is rate-limited per IP address to prevent abuse. Requests that exceed the limit receive a `429 Too Many Requests` response with a `Retry-After` header.

Default limits:

- **5 requests per minute** per IP
- **20 requests per hour** per IP

Tune via `RATE_LIMIT_PER_MINUTE` and `RATE_LIMIT_PER_HOUR` in `.env`. The rate limiter uses in-memory storage, which is suitable for single-process deployments. For multi-worker setups, swap to a Redis-backed storage by updating the `storage_uri` in `app/core/rate_limit.py`.

## Admin Bootstrap

The application can automatically seed an admin user on startup. Set `ADMIN_EMAIL` and `ADMIN_PASSWORD` in your `.env` file:

```bash
ADMIN_EMAIL=admin@alma.com
ADMIN_PASSWORD=change-me-in-production
```

On each startup the seed logic will:
1. **Skip** if `ADMIN_EMAIL` or `ADMIN_PASSWORD` are empty (the default).
2. **Skip** if a user with that email already exists.
3. **Create** an admin account with role `ADMIN` otherwise.

This is idempotent — safe to leave configured across restarts. Once the admin account exists, you can use the admin-only endpoints (`POST /api/admin/attorneys`) to create additional attorney accounts.

> **Production note:** Use a strong password and rotate it after first login. The seed password is only used for initial account creation.

## Email Notifications

When a new lead is submitted, the system sends two emails:

1. **Confirmation** to the prospect ("We received your application")
2. **Notification** to the attorney with the lead's full details (name, email, resume filename)

By default (no email configured), these are logged to the console. To send real emails, configure one of the providers below.

### Option A: Gmail via SMTP (recommended for dev)

Gmail requires an **App Password** — your regular Google password will not work.

**Step 1 — Generate an App Password:**

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Sign in (2-Step Verification must be enabled on your account)
3. Select **Mail** as the app and your device, then click **Generate**
4. Copy the 16-character password (e.g. `abcd efgh ijkl mnop`)

**Step 2 — Add to `.env`:**

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD="abcd efgh ijkl mnop"
EMAIL_FROM=you@gmail.com
ATTORNEY_EMAIL=attorney@alma.com
```

> **Note:** The app password contains spaces — wrap it in double quotes in `.env`.

After updating `.env`, restart the backend:

```bash
docker compose up -d --build app
```

### Option B: Resend API

If you prefer [Resend](https://resend.com), set `RESEND_API_KEY` instead (SMTP settings are ignored when Resend is configured):

```bash
RESEND_API_KEY=re_your_key_here
EMAIL_FROM=noreply@yourdomain.com
ATTORNEY_EMAIL=attorney@alma.com
```

You'll need to verify your sending domain in the Resend dashboard.

### Priority

The system picks the first available provider: **Resend > SMTP > log-only fallback**.

## File Storage

Resume uploads are stored in S3. The app does **not** manage AWS credentials directly — it delegates to [boto3's standard credential chain](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html), which resolves credentials in this order:

1. **Environment variables** — `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` (and optionally `AWS_SESSION_TOKEN`)
2. **Shared credentials file** — `~/.aws/credentials` (set up via `aws configure`)
3. **IAM role** — attached to the EC2 instance, ECS task, or Lambda function

Configure the S3 bucket and region in `.env`:

```bash
S3_BUCKET=my-alma-resumes
S3_REGION=us-east-1
```

**Local development** — set credentials as env vars or run `aws configure`:

```bash
AWS_ACCESS_KEY_ID=AKIAxxxxxxxxxxxxxxxx
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Production** — use an IAM role instead of static keys. Attach a role with `s3:PutObject`, `s3:GetObject`, and `s3:ListBucket` permissions on the target bucket. No credential env vars are needed.

To use an S3-compatible service (e.g., MinIO, LocalStack), set `S3_ENDPOINT_URL`:

```bash
S3_ENDPOINT_URL=http://localhost:9000
```

## Admin Frontend

A lightweight React app for attorneys to log in and review leads.

### Running the Admin UI

```bash
cd frontend/admin
npm install
npm run dev
# → http://localhost:5173
```

### Connecting to Different API Environments

Add a `?api=` query parameter to the URL to target a specific backend:

| URL | Backend |
|-----|---------|
| `http://localhost:5173` | Local API (`http://localhost:8000`) |
| `http://localhost:5173?api=staging` | Staging API (TBD) |
| `http://localhost:5173?api=prod` | Production API (TBD) |

The current environment is shown as a badge in the top-right corner.

## Design Decisions

See `knowledge/` for architecture decision records and open questions:

- [`knowledge/adr-001-database-strategy.md`](knowledge/adr-001-database-strategy.md) — PostgreSQL via Docker
- [`knowledge/adr-002-admin-role-rbac.md`](knowledge/adr-002-admin-role-rbac.md) — Admin role and RBAC
- [`knowledge/adr-003-pluggable-storage-backend.md`](knowledge/adr-003-pluggable-storage-backend.md) — S3 storage backend
- [`knowledge/adr-004-audit-trail.md`](knowledge/adr-004-audit-trail.md) — Audit trail design
- [`knowledge/adr-004-remove-rls-app-layer-auth.md`](knowledge/adr-004-remove-rls-app-layer-auth.md) — App-layer auth over RLS
- [`knowledge/open-questions.md`](knowledge/open-questions.md) — Ambiguities and working assumptions
- [`knowledge/assignment.md`](knowledge/assignment.md) — Original requirements
