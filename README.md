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
Interactive docs (Swagger UI) at **http://localhost:8000/docs**.

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
| `POST` | `/api/auth/register` | Register a user (first user becomes admin, subsequent are attorneys) |
| `POST` | `/api/auth/login` | Login and receive a JWT |

### Internal — Attorney or Admin (requires `Authorization: Bearer <token>`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/leads` | List all leads |
| `GET` | `/api/leads/{id}` | Get a single lead |
| `PATCH` | `/api/leads/{id}` | Update lead state (`PENDING` → `REACHED_OUT`) |

### Admin Only (requires admin JWT)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/admin/attorneys` | Create a new attorney account |
| `GET` | `/api/admin/users` | List all users (admins + attorneys) |
| `GET` | `/api/admin/users/{id}` | Get a single user |
| `DELETE` | `/api/admin/users/{id}` | Delete a user (cannot delete self) |
| `GET` | `/api/admin/files` | List all uploaded files (from S3) |

## API Usage Examples

### Submit a lead (public)

```bash
curl -X POST http://localhost:8000/api/leads \
  -F "first_name=Jane" \
  -F "last_name=Doe" \
  -F "email=jane@example.com" \
  -F "resume=@resume.pdf;type=application/pdf"
```

### Register the first user (becomes admin)

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@alma.com","password":"securepass"}'
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

### Mark a lead as reached out

```bash
curl -X PATCH http://localhost:8000/api/leads/<lead-id> \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"state":"REACHED_OUT"}'
```

## Project Structure

```
app/
├── api/routes/        # Route handlers (thin controllers)
│   ├── admin.py       # Admin-only user management
│   ├── auth.py        # Register + login
│   └── leads.py       # Lead CRUD
├── core/              # Config, security, dependencies
│   ├── config.py      # Environment-driven settings
│   ├── dependencies.py # Auth dependencies (get_current_user, require_admin)
│   └── security.py    # JWT + bcrypt utilities
├── db/
│   ├── seed.py        # Admin user bootstrap on startup
│   └── session.py     # Async SQLAlchemy engine + session
├── models/            # SQLAlchemy ORM models
│   ├── lead.py        # Lead (id, name, email, resume, state)
│   └── user.py        # User (admin/attorney with role enum)
├── schemas/           # Pydantic request/response models
│   ├── auth.py
│   └── lead.py
├── services/          # Business logic layer
│   ├── auth_service.py
│   ├── email_service.py
│   ├── file_service.py
│   ├── lead_service.py
│   └── storage.py     # S3 storage backend
└── main.py            # App entry point
tests/                 # pytest test suite
scripts/               # Utility scripts (smoke test)
knowledge/             # Project context, ADRs, open questions
```

## Configuration

All settings are loaded from environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async database connection string |
| `SECRET_KEY` | — | JWT signing key (change in production!) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT token lifetime |
| `SMTP_HOST` | *(empty)* | SMTP server. If empty, emails log to console |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` / `SMTP_PASSWORD` | — | SMTP credentials |
| `EMAIL_FROM` | `noreply@alma.com` | Sender address |
| `ATTORNEY_EMAIL` | `attorney@alma.com` | Notification recipient |
| `MAX_UPLOAD_SIZE_MB` | `10` | Max resume file size |
| `S3_BUCKET` | — | S3 bucket name (required) |
| `S3_PREFIX` | `resumes` | S3 key prefix for uploaded files |
| `S3_REGION` | *(empty)* | AWS region (e.g., `us-east-1`) |
| `S3_ENDPOINT_URL` | *(empty)* | Custom S3 endpoint (for MinIO / LocalStack) |
| `ADMIN_EMAIL` | *(empty)* | Seed admin email (see [Admin Bootstrap](#admin-bootstrap)) |
| `ADMIN_PASSWORD` | *(empty)* | Seed admin password |

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

## File Storage

Resume uploads are stored in S3. Set `S3_BUCKET` and provide AWS credentials via the standard boto3 chain (env vars `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`, IAM roles, or `~/.aws/credentials`).

```bash
S3_BUCKET=my-alma-resumes
S3_REGION=us-east-1
```

To use an S3-compatible service (e.g., MinIO), set `S3_ENDPOINT_URL`:

```bash
S3_ENDPOINT_URL=http://localhost:9000
```

## Design Decisions

See `knowledge/` for architecture decision records and open questions:

- [`knowledge/adr-001-database-strategy.md`](knowledge/adr-001-database-strategy.md) — PostgreSQL via Docker
- [`knowledge/adr-002-admin-role-rbac.md`](knowledge/adr-002-admin-role-rbac.md) — Admin role and RBAC
- [`knowledge/adr-003-pluggable-storage-backend.md`](knowledge/adr-003-pluggable-storage-backend.md) — S3 storage backend
- [`knowledge/open-questions.md`](knowledge/open-questions.md) — Ambiguities and working assumptions
- [`knowledge/assignment.md`](knowledge/assignment.md) — Original requirements
