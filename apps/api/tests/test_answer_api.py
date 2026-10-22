from unittest.mock import AsyncMock
from uuid import uuid4

from app.core.errors import AppError
from app.documents.answers import AnswerResult
from app.documents.worker import DocumentWorker
from tests.test_document_api import FixtureStorage, paper, pdf_client  # noqa: F401
from tests.test_mentor_discovery import mentor_client  # noqa: F401
from tests.test_pdf_processing import pdf_bytes


def test_answer_http_boundaries(pdf_client, monkeypatch):  # noqa: F811
    client = pdf_client
    uploaded = client.post(
        f"/api/v1/documents/paper/{paper(client)}",
        content=pdf_bytes(["Research methods supported by experimental evidence."]),
        headers={"Content-Type": "application/pdf"},
    )
    endpoint = f"/api/v1/documents/{uploaded.json()['id']}/answers"
    worker = DocumentWorker(
        client.app.state.database.session_factory, FixtureStorage(None), AsyncMock()
    )
    assert client.portal.call(worker.process_one)
    history = endpoint.removesuffix("/answers") + "/reading-history"
    saved = client.get(history)
    assert saved.status_code == 200 and saved.json() == []
    assert saved.headers["cache-control"] == "private, no-store"
    status = client.get(endpoint)
    assert status.status_code == 200
    assert status.json()["enabled"] is False
    assert status.json()["calls_reserved_per_question"] == 3
    assert status.headers["cache-control"] == "private, no-store"
    body = {
        "request_id": str(uuid4()),
        "question": "Research methods?",
        "accepted": True,
        "disclosure_version": status.json()["disclosure_version"],
    }
    assert client.post(endpoint, json=body).status_code == 503
    for changes in (
        {"accepted": False},
        {"accepted": 1},
        {"accepted": "true"},
        {"disclosure_version": "old"},
        {"request_id": "invalid"},
        {"question": " "},
    ):
        assert client.post(endpoint, json={**body, **changes}).status_code == 422
    client.headers.update({"Authorization": "Bearer mentor-user-b"})
    assert client.get(history).status_code == 404
    assert client.get(endpoint).status_code == 404
    assert client.post(endpoint, json=body).status_code == 404
    client.headers.pop("Authorization")
    assert client.get(history).status_code == 401
    assert client.get(endpoint).status_code == 401
    assert client.post(endpoint, json=body).status_code == 401
    client.headers.update({"Authorization": "Bearer mentor-user-a"})
    provider = AsyncMock()
    monkeypatch.setattr(
        "app.api.v1.routes.documents.answers_available", lambda request: True
    )
    monkeypatch.setattr(
        "app.api.v1.routes.documents.GeminiAnswerProvider", lambda settings: provider
    )
    ask = AsyncMock(
        return_value=AnswerResult(
            status="insufficient_evidence", reason="source_insufficient"
        )
    )
    monkeypatch.setattr("app.api.v1.routes.documents.PaperAnswers.ask", ask)
    response = client.post(endpoint, json=body)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert str(ask.call_args.args[2].request_id) == body["request_id"]
    provider.aclose.assert_awaited_once()
    provider.aclose.reset_mock()
    ask.side_effect = AppError(
        code="answer_daily_quota", message="Limit reached", status_code=429
    )
    assert client.post(endpoint, json=body).status_code == 429
    provider.aclose.assert_awaited_once()
