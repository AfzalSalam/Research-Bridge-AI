import asyncio
import json
from uuid import uuid4

import httpx2
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.documents.storage import ObjectKey, StorageUnavailable, SupabaseDocumentStorage

KEY = ObjectKey(uuid4(), uuid4(), "research-documents")


def client(handler):
    return SupabaseDocumentStorage(
        Settings(
            _env_file=None,
            supabase_url="https://fixture.supabase.co",
            supabase_storage_service_key=SecretStr("fixture-secret"),
        ),
        transport=httpx2.MockTransport(handler),
    )


def test_private_transport_and_exact_delete():
    requests = []

    def handler(request):
        requests.append(request)
        assert request.headers["Authorization"] == "Bearer fixture-secret"
        if "/bucket/" in request.url.path:
            return httpx2.Response(200, json={"id": KEY.bucket, "public": False})
        return httpx2.Response(200, content=b"%PDF-fixture")

    async def scenario():
        storage = client(handler)
        try:
            await storage.upload(KEY, b"%PDF-fixture")
            assert await storage.download(KEY) == b"%PDF-fixture"
            await storage.delete(KEY)
        finally:
            await storage.aclose()

    asyncio.run(scenario())
    assert [r.method for r in requests] == ["GET", "POST", "GET", "GET", "DELETE"]
    assert requests[1].content == b"%PDF-fixture"
    assert requests[1].headers["x-upsert"] == "false"
    assert json.loads(requests[-1].content) == {"prefixes": [KEY.path]}
    assert all(r.url.host == "fixture.supabase.co" for r in requests)


@pytest.mark.parametrize(
    "metadata",
    [
        {"id": KEY.bucket, "public": True},
        {"id": KEY.bucket},
        {"id": "wrong", "public": False},
        [],
    ],
)
def test_public_or_unverifiable_bucket_blocks_content(metadata):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx2.Response(200, json=metadata)

    async def scenario():
        storage = client(handler)
        try:
            with pytest.raises(StorageUnavailable, match="storage_bucket_not_private"):
                await storage.download(KEY)
        finally:
            await storage.aclose()

    asyncio.run(scenario())
    assert len(calls) == 1


@pytest.mark.parametrize("status", [302, 401, 403, 500])
def test_failed_requests_do_not_follow_redirects_or_leak_bodies(status):
    def handler(request):
        return httpx2.Response(
            status,
            content=b"private provider diagnostics",
            headers={"Location": "https://example.org"},
        )

    async def scenario():
        storage = client(handler)
        try:
            with pytest.raises(StorageUnavailable) as error:
                await storage.download(KEY)
            assert str(error.value) == "storage_request_failed"
        finally:
            await storage.aclose()

    asyncio.run(scenario())


def test_rate_limit_and_stream_size(monkeypatch):
    monkeypatch.setattr("app.documents.storage.MAX_PDF_BYTES", 20)

    async def scenario():
        storage = client(lambda r: httpx2.Response(429, headers={"Retry-After": "120"}))
        try:
            with pytest.raises(StorageUnavailable) as error:
                await storage.delete(KEY)
            assert error.value.retry_after == 120
        finally:
            await storage.aclose()

        def handler(request):
            if "/bucket/" in request.url.path:
                return httpx2.Response(200, json={"id": KEY.bucket, "public": False})
            return httpx2.Response(200, content=b"x" * 21)

        storage = client(handler)
        try:
            with pytest.raises(StorageUnavailable, match="storage_response_too_large"):
                await storage.download(KEY)
        finally:
            await storage.aclose()

    asyncio.run(scenario())


def test_invalid_key_and_missing_configuration():
    with pytest.raises(ValueError):
        ObjectKey(uuid4(), uuid4(), "../public")
    with pytest.raises(StorageUnavailable, match="storage_not_configured"):
        SupabaseDocumentStorage(
            Settings(
                _env_file=None, supabase_url=None, supabase_storage_service_key=None
            )
        )
