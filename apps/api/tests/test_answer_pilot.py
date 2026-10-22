import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from app.documents.answers import AnswerResult
from scripts import run_answer_pilot as pilot


def test_unavailable_stops_without_abstention_credit(tmp_path, monkeypatch):
    provider = AsyncMock()
    monkeypatch.setattr(pilot, "GeminiAnswerProvider", lambda settings: provider)
    monkeypatch.setattr(
        pilot, "cases", lambda: [({"id": "public", "question": "q"}, ())] * 12
    )
    response = AsyncMock(
        return_value=AnswerResult(status="unavailable", reason="provider_unavailable")
    )
    monkeypatch.setattr(pilot, "answer", response)
    path = tmp_path / "result.json"
    asyncio.run(pilot.run(path))
    result = json.loads(path.read_text())
    assert result["complete"] is False
    assert len(result["cases"]) == 1
    assert result["cases"][0]["result"]["status"] == "unavailable"
    assert response.await_count == 1
    provider.aclose.assert_awaited_once()
    with pytest.raises(ValueError, match="already exists"):
        asyncio.run(pilot.run(path))


def test_observer_redacts_unknown_provider_errors():
    from app.documents.answers import AnswerProviderError

    provider = AsyncMock()
    provider.generate.side_effect = AnswerProviderError("private payload")
    observed = pilot.ObservedProvider(provider)
    with pytest.raises(AnswerProviderError):
        asyncio.run(observed.generate("rules", "data"))
    assert observed.calls[0]["outcome"] == "provider_error"
    assert "private" not in json.dumps(observed.calls)


def test_invalid_answers_remain_failures_and_do_not_hide_later_cases(
    tmp_path, monkeypatch
):
    provider = AsyncMock()
    monkeypatch.setattr(pilot, "GeminiAnswerProvider", lambda settings: provider)
    monkeypatch.setattr(
        pilot,
        "cases",
        lambda: [({"id": str(i), "question": "q"}, ()) for i in range(12)],
    )
    monkeypatch.setattr(pilot.asyncio, "sleep", AsyncMock())
    response = AsyncMock(
        return_value=AnswerResult(
            status="unavailable", reason="invalid_provider_output"
        )
    )
    monkeypatch.setattr(pilot, "answer", response)
    path = tmp_path / "result.json"
    asyncio.run(pilot.run(path))
    report = json.loads(path.read_text())
    assert report["complete"] is True
    assert len(report["cases"]) == 12
    assert all(c["result"]["status"] == "unavailable" for c in report["cases"])
