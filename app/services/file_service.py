from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.services.storage import FileInfo, StorageBackend, build_key, get_storage_backend

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

# Magic byte signatures for allowed file types.
# PDF starts with "%PDF"; DOCX is a ZIP archive starting with "PK\x03\x04".
_MAGIC_SIGNATURES: list[tuple[bytes, str]] = [
    (b"%PDF", "application/pdf"),
    (b"PK\x03\x04", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
]

_MAGIC_READ_SIZE = max(len(sig) for sig, _ in _MAGIC_SIGNATURES)

_backend: StorageBackend | None = None


def _get_backend() -> StorageBackend:
    global _backend
    if _backend is None:
        _backend = get_storage_backend(settings)
    return _backend


def _detect_mime_from_magic(header: bytes) -> str | None:
    """Return the MIME type matching the file's magic bytes, or None."""
    for signature, mime in _MAGIC_SIGNATURES:
        if header.startswith(signature):
            return mime
    return None


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

    detected = _detect_mime_from_magic(contents[:_MAGIC_READ_SIZE])
    if detected is None or detected != file.content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match declared type. Accepted: PDF, DOCX",
        )

    key = build_key(file.filename)
    return await _get_backend().save(contents, key)


def get_resume_url(resume_path: str) -> str:
    """Generate a download URL for the given stored resume reference."""
    return _get_backend().url(resume_path)


async def list_files() -> list[FileInfo]:
    return await _get_backend().list_files()
