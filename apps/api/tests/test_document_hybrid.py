import asyncio
from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.db.models import DocumentPage
from app.documents.contracts import PdfChunk
from app.documents.embeddings import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    EmbeddingBatch,
)
from app.documents.hybrid import fuse, retrieve_hybrid
from app.documents.retrieval import PassageQuery
from app.documents.vectors import VectorRepository
from tests.test_document_repository import exercise


def chunk(page, text, start=0):
    return PdfChunk(page=page, start=start, end=start + len(text), text=text)


def test_agreement_outranks_single_source_and_duplicates_cannot_boost():
    a, b, c = chunk(1, "first"), chunk(2, "shared"), chunk(3, "third")
    pages = {1: a.text, 2: b.text, 3: c.text}
    assert fuse([[a, b], [c, b]], pages, limit=3) == [b, a, c]
    assert fuse([[a, a, a, b], [c, b]], pages, limit=3) == [b, a, c]
    assert fuse([[a], [c]], pages, limit=1) == [a]


def test_invalid_sources_overlap_and_empty_results():
    source = "graph attention methods"
    a = chunk(1, source[:15])
    overlap = chunk(1, source[6:], 6)
    forged = chunk(1, "invented")
    missing = chunk(2, "absent")
    assert fuse([[forged, missing, a], [overlap]], {1: source}, limit=10) == [
        a,
        overlap,
    ]
    assert fuse([[forged], []], {1: source}, limit=5) == []
    with pytest.raises(ValueError):
        fuse([], {}, limit=11)


def test_hybrid_checks_owner_and_preserves_exact_citations(
    migrated_database_url, monkeypatch
):
    async def scenario(session, sessions, owner, doc):
        doc.status = "ready"
        texts = ["graph attention method", "molecular structure relationships"]
        for number, text in enumerate(texts, 1):
            session.add(
                DocumentPage(
                    document_id=doc.id,
                    number=number,
                    text=text,
                    chunks=[{"start": 0, "end": len(text), "text": text}],
                )
            )
        await session.commit()
        calls = []

        async def nearest(self, user, document, vector, *, limit):
            calls.append((user, document, limit))
            return [chunk(2, texts[1]), chunk(1, "forged")]

        monkeypatch.setattr(VectorRepository, "nearest", nearest)
        embedding = EmbeddingBatch(
            model=EMBEDDING_MODEL,
            dimensions=EMBEDDING_DIMENSIONS,
            vectors=(tuple([1.0] + [0.0] * (EMBEDDING_DIMENSIONS - 1)),),
            prompt_tokens=1,
        )
        request = PassageQuery(query="graph", limit=2)
        with pytest.raises(AppError) as error:
            await retrieve_hybrid(session, uuid4(), doc.id, request, embedding)
        assert error.value.status_code == 404
        assert not calls
        result = await retrieve_hybrid(session, owner.id, doc.id, request, embedding)
        assert [p.page for p in result.passages] == [1, 2]
        assert calls == [(owner.id, doc.id, 10)]
        for passage in result.passages:
            assert texts[passage.page - 1][passage.start : passage.end] == passage.text

    asyncio.run(exercise(migrated_database_url, scenario))


@pytest.mark.parametrize("overlap", [1, 150, 1199])
def test_partial_overlap_preserves_unique_text(overlap):
    source = "x" * 2400
    first = chunk(1, source[:1200])
    start = 1200 - overlap
    second = chunk(1, source[start : start + 1200], start)
    assert fuse([[first], [second]], {1: source}, limit=10) == [first, second]
    assert fuse([[first], [second]], {1: source}, limit=1) == [first]


def test_containment_does_not_discard_extensions_or_other_pages():
    source = "first detail and another detail"
    outer = chunk(1, source)
    inner = chunk(1, source[6:12], 6)
    assert fuse([[outer, inner]], {1: source}, limit=10) == [outer]
    assert fuse([[inner, outer]], {1: source}, limit=10) == [inner, outer]
    other = chunk(2, source[6:12], 6)
    assert fuse([[outer, other]], {1: source, 2: source}, limit=10) == [outer, other]


def test_fusion_agreement_keeps_neighbor_with_distinct_evidence():
    source = "x" * 2250
    evidence = chunk(1, source[:1200])
    neighbor = chunk(1, source[1050:], 1050)
    assert fuse([[neighbor], [evidence, neighbor]], {1: source}, limit=5) == [
        neighbor,
        evidence,
    ]
