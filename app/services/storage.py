"""
Pluggable storage backends for file uploads.

Set STORAGE_BACKEND=local (default) or STORAGE_BACKEND=s3 in your environment.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import aiofiles

if TYPE_CHECKING:
    from app.core.config import Settings


@dataclass
class FileInfo:
    key: str
    size_bytes: int
    last_modified: datetime


class StorageBackend(ABC):
    """Interface that all storage backends must implement."""

    @abstractmethod
    async def save(self, data: bytes, key: str) -> str:
        """Persist *data* under *key* and return the stored reference (path or S3 key)."""

    @abstractmethod
    def url(self, stored_ref: str) -> str:
        """Return a download URL for a previously stored object.

        *stored_ref* is the value returned by :meth:`save`.
        """

    @abstractmethod
    async def list_files(self) -> list[FileInfo]:
        """Return metadata for all stored files."""


class LocalStorageBackend(StorageBackend):
    def __init__(self, upload_dir: str) -> None:
        self._upload_dir = Path(upload_dir)

    async def save(self, data: bytes, key: str) -> str:
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        filepath = self._upload_dir / key
        async with aiofiles.open(filepath, "wb") as f:
            await f.write(data)
        return str(filepath)

    def url(self, stored_ref: str) -> str:
        return str(Path(stored_ref))

    _RESUME_EXTENSIONS = {".pdf", ".docx"}

    async def list_files(self) -> list[FileInfo]:
        if not self._upload_dir.exists():
            return []
        files = []
        for p in sorted(self._upload_dir.iterdir()):
            if p.is_file() and p.suffix.lower() in self._RESUME_EXTENSIONS:
                stat = p.stat()
                files.append(FileInfo(
                    key=p.name,
                    size_bytes=stat.st_size,
                    last_modified=datetime.fromtimestamp(stat.st_mtime),
                ))
        return files


class S3StorageBackend(StorageBackend):
    """Stores files in an S3-compatible bucket using boto3."""

    def __init__(
        self,
        bucket: str,
        prefix: str = "resumes",
        region: str | None = None,
        endpoint_url: str | None = None,
    ) -> None:
        import boto3

        self._bucket = bucket
        self._prefix = prefix
        client_kwargs: dict = {}
        if region:
            client_kwargs["region_name"] = region
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
        self._client = boto3.client("s3", **client_kwargs)

    async def save(self, data: bytes, key: str) -> str:
        s3_key = f"{self._prefix}/{key}" if self._prefix else key
        self._client.put_object(Bucket=self._bucket, Key=s3_key, Body=data)
        return s3_key

    _PRESIGNED_EXPIRY = 300  # 5 minutes

    def url(self, stored_ref: str) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self._bucket,
                "Key": stored_ref,
                "ResponseContentDisposition": "attachment",
            },
            ExpiresIn=self._PRESIGNED_EXPIRY,
        )

    async def list_files(self) -> list[FileInfo]:
        prefix = f"{self._prefix}/" if self._prefix else ""
        paginator = self._client.get_paginator("list_objects_v2")
        files = []
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                files.append(FileInfo(
                    key=obj["Key"],
                    size_bytes=obj["Size"],
                    last_modified=obj["LastModified"],
                ))
        return files


def build_key(original_filename: str | None) -> str:
    ext = Path(original_filename).suffix if original_filename else ".pdf"
    return f"{uuid.uuid4()}{ext}"


def get_storage_backend(settings: Settings) -> StorageBackend:
    backend = settings.storage_backend.lower()
    if backend == "local":
        return LocalStorageBackend(upload_dir=settings.upload_dir)
    if backend == "s3":
        if not settings.s3_bucket:
            raise RuntimeError("STORAGE_BACKEND=s3 requires S3_BUCKET to be set")
        return S3StorageBackend(
            bucket=settings.s3_bucket,
            prefix=settings.s3_prefix,
            region=settings.s3_region or None,
            endpoint_url=settings.s3_endpoint_url or None,
        )
    raise ValueError(f"Unknown STORAGE_BACKEND: {backend!r}. Use 'local' or 's3'.")
