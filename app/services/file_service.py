from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.services.storage import FileInfo, StorageBackend, build_key, get_storage_backend

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

_backend: StorageBackend | None = None


def _get_backend() -> StorageBackend:
    global _backend
    if _backend is None:
        _backend = get_storage_backend(settings)
    return _backend


async def save_resume(file: UploadFile) -> str:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File type not allowed. Accepted: PDF, DOCX",
        )

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(1024 * 1024):
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Max size: {settings.max_upload_size_mb} MB",
            )
        chunks.append(chunk)
    contents = b"".join(chunks)

    key = build_key(file.filename)
    return await _get_backend().save(contents, key)


async def list_files() -> list[FileInfo]:
    return await _get_backend().list_files()
