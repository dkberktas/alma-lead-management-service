"""S3 storage backend for file uploads."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings


@dataclass
class FileInfo:
    key: str
    size_bytes: int
    last_modified: datetime


class S3StorageBackend:
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

    def url(self, key: str) -> str:
        s3_key = f"{self._prefix}/{key}" if self._prefix else key
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": s3_key},
            ExpiresIn=3600,
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


def create_s3_backend(settings: Settings) -> S3StorageBackend:
    if not settings.s3_bucket:
        raise RuntimeError("S3_BUCKET must be set")
    return S3StorageBackend(
        bucket=settings.s3_bucket,
        prefix=settings.s3_prefix,
        region=settings.s3_region or None,
        endpoint_url=settings.s3_endpoint_url or None,
    )
