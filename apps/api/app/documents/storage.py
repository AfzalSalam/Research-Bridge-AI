"""Private Supabase transport. No arbitrary paths or public document URLs."""

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import httpx2

from app.core.config import Settings
from app.documents.contracts import MAX_PDF_BYTES


class StorageUnavailable(Exception):
    def __init__(
        self, code: str = "storage_unavailable", retry_after: int = 30
    ) -> None:
        super().__init__(code)
        self.code = code
        self.retry_after = max(30, min(retry_after, 3600))


@dataclass(frozen=True)
class ObjectKey:
    owner_id: UUID
    document_id: UUID
    bucket: str

    def __post_init__(self) -> None:
        if not isinstance(self.owner_id, UUID) or not isinstance(
            self.document_id, UUID
        ):
            raise ValueError("Object identities must be UUIDs")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", self.bucket):
            raise ValueError("Invalid private bucket name")

    @property
    def path(self) -> str:
        return f"{self.owner_id}/{self.document_id}.pdf"


class DocumentStorage(Protocol):
    async def upload(self, key: ObjectKey, content: bytes) -> None: ...
    async def download(self, key: ObjectKey) -> bytes: ...
    async def delete(self, key: ObjectKey) -> None: ...


class SupabaseDocumentStorage:
    def __init__(
        self, settings: Settings, *, transport: httpx2.AsyncBaseTransport | None = None
    ) -> None:
        if not settings.supabase_url or not settings.supabase_storage_service_key:
            raise StorageUnavailable("storage_not_configured")
        self._origin = settings.supabase_url + "/storage/v1/"
        secret = settings.supabase_storage_service_key.get_secret_value()
        self._client = httpx2.AsyncClient(
            headers={
                "apikey": secret,
                "Authorization": f"Bearer {secret}",
                "Accept-Encoding": "identity",
            },
            timeout=httpx2.Timeout(30, connect=5, pool=5),
            limits=httpx2.Limits(max_connections=4, max_keepalive_connections=2),
            follow_redirects=False,
            trust_env=False,
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        limit: int = 65536,
        content: bytes | None = None,
        payload: dict[str, list[str]] | None = None,
    ) -> bytes:
        headers = (
            {
                "Content-Type": "application/pdf",
                "x-upsert": "false",
                "Cache-Control": "no-store",
            }
            if content is not None
            else {}
        )
        try:
            async with asyncio.timeout(60):
                async with self._client.stream(
                    method,
                    self._origin + path,
                    content=content,
                    json=payload,
                    headers=headers,
                ) as response:
                    if response.status_code == 429:
                        retry = response.headers.get("Retry-After", "30")
                        raise StorageUnavailable(
                            "storage_rate_limited",
                            int(retry) if retry.isdecimal() else 30,
                        )
                    if not 200 <= response.status_code < 300:
                        raise StorageUnavailable("storage_request_failed")
                    if (
                        response.headers.get("Content-Encoding", "identity")
                        != "identity"
                    ):
                        raise StorageUnavailable("storage_encoded_response")
                    data = bytearray()
                    async for chunk in response.aiter_bytes(65536):
                        if len(data) + len(chunk) > limit:
                            raise StorageUnavailable("storage_response_too_large")
                        data.extend(chunk)
                    return bytes(data)
        except (httpx2.RequestError, TimeoutError) as exc:
            raise StorageUnavailable() from exc

    async def _private(self, key: ObjectKey) -> None:
        raw = await self._request("GET", f"bucket/{key.bucket}")
        try:
            bucket = json.loads(raw)
        except (ValueError, UnicodeDecodeError) as exc:
            raise StorageUnavailable("storage_invalid_bucket_response") from exc
        if (
            not isinstance(bucket, dict)
            or bucket.get("id") != key.bucket
            or bucket.get("public") is not False
        ):
            raise StorageUnavailable("storage_bucket_not_private")

    async def upload(self, key: ObjectKey, content: bytes) -> None:
        if not content.startswith(b"%PDF-") or len(content) > MAX_PDF_BYTES:
            raise ValueError("Expected a PDF within the upload limit")
        await self._private(key)
        await self._request("POST", f"object/{key.bucket}/{key.path}", content=content)

    async def download(self, key: ObjectKey) -> bytes:
        await self._private(key)
        return await self._request(
            "GET", f"object/{key.bucket}/{key.path}", limit=MAX_PDF_BYTES
        )

    async def delete(self, key: ObjectKey) -> None:
        # Allow cleanup even if an administrator makes a bucket public.
        await self._request(
            "DELETE", f"object/{key.bucket}", payload={"prefixes": [key.path]}
        )
