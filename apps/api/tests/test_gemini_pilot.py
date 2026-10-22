import asyncio
from unittest.mock import AsyncMock

import pytest

from app.core.config import Settings
from app.documents.embeddings import EmbeddingError
from scripts import run_gemini_paper_pilot as pilot
from scripts.run_public_paper_pilot import source_chunks


def manifest():
    return {"queries": [{"id": "q", "question": "public question"}]}


def test_chunk_boundaries_match_frozen_pipeline():
    chunks = source_chunks(["x" * 2300])
    assert [(c.page, c.start, c.end) for c in chunks] == [
        (1, 0, 1200),
        (1, 1050, 2250),
        (1, 2100, 2300),
    ]
    assert source_chunks(["   "]) == []


def test_preflight_bounds_before_provider(monkeypatch, tmp_path):
    monkeypatch.setattr(pilot, "load_source", lambda *args: ["x" * 2300])
    texts, queries = pilot.preflight(tmp_path / "public.pdf", manifest())
    assert len(texts) == 3 and len(queries) == 1
    monkeypatch.setattr(pilot, "MAX_REQUESTS", 3)
    with pytest.raises(ValueError, match="request budget"):
        pilot.preflight(tmp_path / "public.pdf", manifest())
    monkeypatch.setattr(pilot, "MAX_REQUESTS", 100)
    monkeypatch.setattr(pilot, "MAX_INPUT_BYTES", 1)
    with pytest.raises(ValueError, match="byte budget"):
        pilot.preflight(tmp_path / "public.pdf", manifest())


def test_provider_error_stops_pilot_and_closes_clients(monkeypatch, tmp_path):
    monkeypatch.setattr(
        pilot, "preflight", lambda *args: (["public"], manifest()["queries"])
    )
    client = AsyncMock()
    client.embed.side_effect = EmbeddingError("embedding_provider_unavailable")
    monkeypatch.setattr(pilot, "GeminiEmbeddings", lambda *args, **kwargs: client)
    with pytest.raises(EmbeddingError):
        asyncio.run(
            pilot.prepare(tmp_path / "public.pdf", manifest(), Settings(_env_file=None))
        )
    assert client.embed.await_count == 1
    assert client.aclose.await_count == 2
