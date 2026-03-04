# ADR-003: S3 Storage Backend

## Status
Accepted — supersedes the original pluggable (Local + S3) design

## Context
Resume file uploads were originally handled by a pluggable `StorageBackend` abstraction with two implementations: `LocalStorageBackend` (disk) and `S3StorageBackend`. The local backend existed to reduce friction during development but added code, test surface, and a startup-validation guard to prevent it from reaching production.

In practice the team uses S3-compatible services (AWS S3, MinIO, LocalStack) across all environments, and the local backend was unused outside of tests. Maintaining two backends added complexity without delivering value.

## Decision
Remove `LocalStorageBackend` and the `STORAGE_BACKEND` / `UPLOAD_DIR` configuration. The application now uses S3 exclusively via `S3StorageBackend`.

- `S3_BUCKET` is required in all environments.
- `S3_ENDPOINT_URL` is available for S3-compatible services (MinIO, LocalStack) but not required — pointing at a real S3 bucket works just as well.
- Tests use a lightweight in-memory stub (`InMemoryStorageBackend` in `conftest.py`) — no boto3 or filesystem needed.

## Alternatives Considered
- **Keep both backends** — rejected; the local backend was unused in practice and added maintenance overhead.
- **Abstract interface (ABC) with single S3 impl** — rejected as unnecessary indirection when there is only one concrete backend.

## Consequences
- `aiofiles` dependency removed.
- `STORAGE_BACKEND` and `UPLOAD_DIR` env vars removed; `S3_BUCKET` is now always required.
- Local development uses the same S3 bucket (or an S3-compatible service if preferred).
- Startup validation (`_validate_storage_config`) removed since there is no longer a backend to gate.
