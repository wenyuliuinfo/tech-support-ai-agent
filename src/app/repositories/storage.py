"""MinIO / S3-compatible object storage repository."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from aioboto3 import Session

from config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StorageObject:
    key: str
    size: int
    last_modified: str | None = None
    etag: str | None = None


class StorageRepository:
    """Async wrapper around the MinIO S3 API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._endpoint_url = settings.minio_endpoint
        self._access_key = settings.minio_access_key
        self._secret_key = settings.minio_secret_key
        self._bucket = settings.minio_bucket_name
        self._use_ssl = settings.minio_use_ssl
        self._session = Session()

    def _client(self) -> Any:
        return self._session.client(
            "s3",
            endpoint_url=self._endpoint_url,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            use_ssl=self._use_ssl,
        )

    async def upload(
        self,
        key: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> StorageObject:
        async with self._client() as client:
            await client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
            )
            head = await client.head_object(Bucket=self._bucket, Key=key)
            return self._storage_object(key, head)

    async def get(self, key: str) -> bytes:
        async with self._client() as client:
            response = await client.get_object(Bucket=self._bucket, Key=key)
            async with response["Body"] as stream:
                return await stream.read()

    async def list(self, prefix: str) -> list[StorageObject]:
        objects: list[StorageObject] = []
        async with self._client() as client:
            paginator = client.get_paginator("list_objects_v2")
            async for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
                for item in page.get("Contents", []):
                    objects.append(self._storage_object(item["Key"], item))
        return objects

    async def archive(self, key: str) -> StorageObject:
        archive_key = self._archive_key(key)
        async with self._client() as client:
            await client.copy_object(
                Bucket=self._bucket,
                Key=archive_key,
                CopySource={"Bucket": self._bucket, "Key": key},
            )
            await client.delete_object(Bucket=self._bucket, Key=key)
            head = await client.head_object(Bucket=self._bucket, Key=archive_key)
            return self._storage_object(archive_key, head)

    @staticmethod
    def _archive_key(key: str) -> str:
        prefix = "knowledge-base/"
        if key.startswith(prefix):
            return "_archive/" + key[len(prefix) :]
        return "_archive/" + key.lstrip("/")

    @staticmethod
    def _storage_object(key: str, head: Any) -> StorageObject:
        return StorageObject(
            key=key,
            size=int(head.get("ContentLength", head.get("Size", 0))),
            last_modified=str(head.get("LastModified", "")),
            etag=str(head.get("ETag", "")),
        )
