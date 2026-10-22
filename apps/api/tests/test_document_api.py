from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import SecretStr

from app.documents.worker import DocumentWorker
from tests.test_mentor_discovery import mentor_client  # noqa: F401
from tests.test_pdf_processing import pdf_bytes


class FixtureStorage:
    files = {}

    def __init__(self, settings):
        pass

    async def upload(self, key, content):
        self.files[key.path] = content

    async def download(self, key):
        return self.files[key.path]

    async def aclose(self):
        pass


@pytest.fixture
def pdf_client(mentor_client, monkeypatch):  # noqa: F811
    settings = mentor_client.app.state.settings
    settings.document_embedding_provider = "openai"
    settings.document_uploads_enabled = True
    settings.supabase_url = "https://fixture.supabase.co"
    settings.supabase_storage_service_key = SecretStr("fixture")
    settings.document_scanner_host = "fixture"
    FixtureStorage.files = {}
    monkeypatch.setattr(
        "app.api.v1.routes.documents.SupabaseDocumentStorage", FixtureStorage
    )
    return mentor_client


def paper(client):
    response = client.post(
        "/api/v1/discovery/papers", json={"query": "machine learning", "limit": 10}
    )
    assert response.status_code == 200
    return response.json()["papers"][0]["id"]


def test_upload_process_read_and_cross_account_denial(pdf_client, monkeypatch):
    client = pdf_client
    paper_id = paper(client)
    endpoint = f"/api/v1/documents/paper/{paper_id}"
    content = pdf_bytes(
        ["Research methods and findings are supported by the evaluation dataset."]
    )
    uploaded = client.post(
        endpoint, content=content, headers={"Content-Type": "application/pdf"}
    )
    assert uploaded.status_code == 202, uploaded.text
    id = uploaded.json()["id"]
    path = f"/api/v1/documents/{id}"
    assert client.get(path + "/pages").status_code == 409
    assert client.get(path + "/file").status_code == 409
    assert (
        client.post(path + "/passages", json={"query": "research"}).status_code == 409
    )
    assert client.get(endpoint).json()["documents"][0]["status"] == "quarantined"
    worker = DocumentWorker(
        client.app.state.database.session_factory, FixtureStorage(None), AsyncMock()
    )
    assert client.portal.call(worker.process_one)
    assert client.get(path).json()["status"] == "ready"
    assert "Research methods" in client.get(path + "/pages").json()[0]["text"]
    assert client.get(path + "/pages").headers["Cache-Control"] == "private, no-store"
    passages = client.post(path + "/passages", json={"query": "research methods"})
    assert passages.status_code == 200
    assert passages.json()["passages"][0]["page"] == 1
    assert passages.headers["cache-control"] == "private, no-store"
    assert (
        client.post(path + "/passages", json={"query": "x", "limit": 11}).status_code
        == 422
    )
    query_consent = {
        "query": "research",
        "accepted": True,
        "disclosure_version": "paper-query-embeddings-v1",
    }
    assert (
        client.post(path + "/semantic-passages", json=query_consent).status_code == 503
    )
    assert (
        client.post(
            path + "/semantic-passages", json={**query_consent, "accepted": False}
        ).status_code
        == 422
    )
    assert (
        client.post(
            path + "/semantic-passages",
            json={**query_consent, "disclosure_version": "old"},
        ).status_code
        == 422
    )
    consent = {"accepted": True, "disclosure_version": "paper-embeddings-v1"}
    assert client.get(path + "/index").json()["enabled"] is False
    assert client.post(path + "/index", json=consent).status_code == 503
    monkeypatch.setattr(
        "app.api.v1.routes.documents.indexing_available", lambda request: True
    )
    assert (
        client.post(path + "/index", json={**consent, "accepted": False}).status_code
        == 422
    )
    assert (
        client.post(
            path + "/index", json={**consent, "disclosure_version": "old"}
        ).status_code
        == 422
    )
    queued = client.post(path + "/index", json=consent)
    assert queued.status_code == 202
    assert client.post(path + "/index", json=consent).json() == queued.json()
    assert client.get(path + "/index").json()["status"] == "queued"
    from uuid import UUID

    from app.documents.embeddings import EmbeddingError
    from app.documents.hybrid import HybridResult

    with monkeypatch.context() as mocked:
        provider = AsyncMock()
        mocked.setattr(
            "app.api.v1.routes.documents.create_embedder", lambda _, **kwargs: provider
        )
        search = AsyncMock(return_value=HybridResult(document_id=UUID(id), passages=[]))
        mocked.setattr("app.api.v1.routes.documents.SemanticSearch.search", search)
        result = client.post(path + "/semantic-passages", json=query_consent)
        assert result.status_code == 200
        assert result.headers["cache-control"] == "private, no-store"
        assert result.json()["passages"] == []
        assert search.call_args.args[1] == UUID(id)
        provider.aclose.assert_awaited_once()
        search.side_effect = EmbeddingError("private-provider-detail")
        failed = client.post(path + "/semantic-passages", json=query_consent)
        assert failed.status_code == 503
        assert "private-provider-detail" not in failed.text
        assert provider.aclose.await_count == 2

    original = client.get(path + "/file")
    assert original.status_code == 200
    assert original.content == content
    assert original.headers["cache-control"] == "private, no-store"
    assert original.headers["content-type"] == "application/pdf"
    key = next(iter(FixtureStorage.files))
    FixtureStorage.files[key] = b"%PDF-tampered"
    assert client.get(path + "/file").status_code == 409
    FixtureStorage.files[key] = content
    client.headers.update({"Authorization": "Bearer mentor-user-b"})
    assert client.get(endpoint).json()["documents"] == []
    for suffix in ("", "/pages", "/file", "/index"):
        assert client.get(path + suffix).status_code == 404
    assert (
        client.post(path + "/passages", json={"query": "research"}).status_code == 404
    )
    assert (
        client.post(path + "/semantic-passages", json=query_consent).status_code == 404
    )
    assert client.delete(path + "/index").status_code == 404
    assert client.post(path + "/index", json=consent).status_code == 404
    assert client.delete(path).status_code == 404
    client.headers.update({"Authorization": "Bearer mentor-user-a"})
    assert client.delete(path + "/index").status_code == 204
    assert client.get(path + "/index").json()["status"] == "cancelled"
    assert client.delete(path).status_code == 204
    assert client.get(path).status_code == 404


def test_disabled_unauthenticated_and_bounded_uploads(pdf_client):
    client = pdf_client
    endpoint = f"/api/v1/documents/paper/{uuid4()}"
    assert (
        client.post(
            endpoint, content=b"x", headers={"Content-Type": "text/plain"}
        ).status_code
        == 415
    )
    assert (
        client.post(
            endpoint,
            content=b"%PDF-",
            headers={
                "Content-Type": "application/pdf",
                "Content-Length": str(21 * 1024 * 1024),
            },
        ).status_code
        == 413
    )
    client.app.state.settings.document_uploads_enabled = False
    assert not client.get(endpoint).json()["uploads_enabled"]
    assert client.post(endpoint, content=b"%PDF-").status_code == 503
    client.headers.pop("Authorization")
    assert client.get(endpoint).status_code == 401


def test_upload_throttle_counts_committed_intents(pdf_client):
    client = pdf_client
    endpoint = f"/api/v1/documents/paper/{paper(client)}"
    for _ in range(5):
        assert (
            client.post(
                endpoint,
                content=b"%PDF-fixture",
                headers={"Content-Type": "application/pdf"},
            ).status_code
            == 202
        )
    assert (
        client.post(
            endpoint,
            content=b"%PDF-fixture",
            headers={"Content-Type": "application/pdf"},
        ).status_code
        == 429
    )


def test_gemini_api_refuses_old_provider_consent(pdf_client, monkeypatch):
    client = pdf_client
    uploaded = client.post(
        f"/api/v1/documents/paper/{paper(client)}",
        content=pdf_bytes(
            ["Research methods are supported by this evaluation dataset."]
        ),
        headers={"Content-Type": "application/pdf"},
    )
    assert uploaded.status_code == 202
    worker = DocumentWorker(
        client.app.state.database.session_factory, FixtureStorage(None), AsyncMock()
    )
    assert client.portal.call(worker.process_one)
    client.app.state.settings.document_embedding_provider = "gemini"
    monkeypatch.setattr(
        "app.api.v1.routes.documents.indexing_available", lambda request: True
    )
    path = f"/api/v1/documents/{uploaded.json()['id']}/index"
    status = client.get(path).json()
    assert status["provider"] == "Google Gemini"
    assert status["disclosure_version"] == "paper-gemini-v1"
    assert status["query_disclosure_version"] == "paper-query-gemini-v1"
    assert (
        client.post(
            path, json={"accepted": True, "disclosure_version": "paper-embeddings-v1"}
        ).status_code
        == 409
    )
    assert client.get(path).json()["status"] == "not_started"
    assert (
        client.post(
            path, json={"accepted": True, "disclosure_version": "paper-gemini-v1"}
        ).status_code
        == 202
    )
