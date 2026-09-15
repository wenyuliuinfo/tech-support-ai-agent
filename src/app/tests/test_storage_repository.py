"""Storage repository tests using a stubbed aioboto3 client."""

import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# aioboto3 is an optional local dependency in this workspace; stub it before
# importing the repository so the tests can exercise the repository contract
# without a running MinIO instance.
_fake_aioboto3 = ModuleType("aioboto3")


class _FakeSession:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def client(self, *args, **kwargs):
        return MagicMock()


_fake_aioboto3.Session = _FakeSession
sys.modules["aioboto3"] = _fake_aioboto3

from repositories.storage import StorageObject, StorageRepository  # noqa: E402


def _settings():
    settings = MagicMock()
    settings.minio_endpoint = "http://localhost:9000"
    settings.minio_access_key = "access-key"
    settings.minio_secret_key = "secret-key"
    settings.minio_bucket_name = "test-bucket"
    settings.minio_use_ssl = False
    return settings


def _client_context(client):
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=client)
    context.__aexit__ = AsyncMock(return_value=False)
    return context


@pytest.fixture
def storage_repo():
    with patch("repositories.storage.get_settings", return_value=_settings()):
        return StorageRepository()


class TestStorageRepository:
    @pytest.mark.asyncio
    async def test_upload(self, storage_repo):
        client = AsyncMock()
        client.put_object = AsyncMock()
        client.head_object = AsyncMock(
            return_value={
                "ContentLength": 5,
                "LastModified": "2026-09-15T00:00:00Z",
                "ETag": "abc",
            }
        )
        storage_repo._client = MagicMock(return_value=_client_context(client))

        result = await storage_repo.upload("knowledge-base/doc/v1/a.md", b"hello", "text/markdown")

        client.put_object.assert_awaited_once()
        assert result == StorageObject(
            key="knowledge-base/doc/v1/a.md",
            size=5,
            last_modified="2026-09-15T00:00:00Z",
            etag="abc",
        )

    @pytest.mark.asyncio
    async def test_get(self, storage_repo):
        stream = AsyncMock()
        stream.__aenter__ = AsyncMock(return_value=stream)
        stream.__aexit__ = AsyncMock(return_value=False)
        stream.read = AsyncMock(return_value=b"content")

        client = AsyncMock()
        client.get_object = AsyncMock(return_value={"Body": stream})
        storage_repo._client = MagicMock(return_value=_client_context(client))

        result = await storage_repo.get("knowledge-base/doc/v1/a.md")

        assert result == b"content"
        client.get_object.assert_awaited_once_with(
            Bucket="test-bucket",
            Key="knowledge-base/doc/v1/a.md",
        )

    @pytest.mark.asyncio
    async def test_list(self, storage_repo):
        async def pages():
            yield {
                "Contents": [
                    {
                        "Key": "knowledge-base/doc/v1/a.md",
                        "Size": 7,
                        "LastModified": "2026-09-15T00:00:00Z",
                        "ETag": "etag",
                    }
                ]
            }

        paginator = AsyncMock()
        paginator.paginate = MagicMock(return_value=pages())
        client = AsyncMock()
        client.get_paginator = MagicMock(return_value=paginator)
        storage_repo._client = MagicMock(return_value=_client_context(client))

        result = await storage_repo.list("knowledge-base/doc/")

        assert result == [
            StorageObject(
                key="knowledge-base/doc/v1/a.md",
                size=7,
                last_modified="2026-09-15T00:00:00Z",
                etag="etag",
            )
        ]
        client.get_paginator.assert_called_once_with("list_objects_v2")

    @pytest.mark.asyncio
    async def test_archive(self, storage_repo):
        client = AsyncMock()
        client.copy_object = AsyncMock()
        client.delete_object = AsyncMock()
        client.head_object = AsyncMock(
            return_value={
                "ContentLength": 11,
                "LastModified": "2026-09-15T00:00:00Z",
                "ETag": "archive-etag",
            }
        )
        storage_repo._client = MagicMock(return_value=_client_context(client))

        result = await storage_repo.archive("knowledge-base/doc/v1/a.md")

        client.copy_object.assert_awaited_once_with(
            Bucket="test-bucket",
            Key="_archive/doc/v1/a.md",
            CopySource={"Bucket": "test-bucket", "Key": "knowledge-base/doc/v1/a.md"},
        )
        client.delete_object.assert_awaited_once_with(
            Bucket="test-bucket",
            Key="knowledge-base/doc/v1/a.md",
        )
        assert result.key == "_archive/doc/v1/a.md"
