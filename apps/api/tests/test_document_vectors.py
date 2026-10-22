import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.db.models import DocumentPage, DocumentVector
from app.documents.contracts import PdfChunk
from app.documents.embeddings import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    EmbeddingBatch,
)
from app.documents.hybrid import retrieve_hybrid
from app.documents.retrieval import PassageQuery
from app.documents.vectors import VectorRepository
from tests.test_document_repository import exercise


def batch(axis=0):
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[axis] = 1.0
    return EmbeddingBatch(EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, (tuple(vector),), 5)


async def seed(session, doc):
    doc.status = "ready"
    content = "Graph attention method."
    page = DocumentPage(
        document_id=doc.id,
        number=1,
        text=content,
        chunks=[{"start": 0, "end": len(content), "text": content}],
    )
    session.add(page)
    await session.commit()
    return page, PdfChunk(page=1, start=0, end=len(content), text=content)


async def check_vectors(session, sessions, owner, doc):
    page, chunk = await seed(session, doc)
    repo = VectorRepository(session)
    with pytest.raises(AppError) as error:
        await repo.replace(uuid4(), doc.id, [chunk], batch())
    assert error.value.status_code == 404
    await repo.replace(owner.id, doc.id, [chunk], batch())
    await session.commit()
    assert await session.scalar(select(func.count()).select_from(DocumentVector)) == 1
    # Replacing the same index is idempotent, not another duplicate record.
    await repo.replace(owner.id, doc.id, [chunk], batch(1))
    await session.commit()
    assert await session.scalar(select(func.count()).select_from(DocumentVector)) == 1
    with pytest.raises(AppError):
        await repo.replace(
            owner.id, doc.id, [chunk.model_copy(update={"text": "forged"})], batch()
        )
    assert await session.scalar(select(func.count()).select_from(DocumentVector)) == 1
    with pytest.raises(AppError) as error:
        await repo.nearest(uuid4(), doc.id, batch())
    assert error.value.status_code == 404
    if session.get_bind().dialect.name == "postgresql":
        result = await repo.nearest(owner.id, doc.id, batch(1))
        assert result == [chunk]
        second = PdfChunk(page=2, start=0, end=12, text="Other method")
        session.add(
            DocumentPage(
                document_id=doc.id,
                number=2,
                text=second.text,
                chunks=[{"start": 0, "end": 12, "text": second.text}],
            )
        )
        await session.flush()
        both = EmbeddingBatch(
            EMBEDDING_MODEL,
            EMBEDDING_DIMENSIONS,
            (batch(1).vectors[0], batch(0).vectors[0]),
            10,
        )
        await repo.replace(owner.id, doc.id, [chunk, second], both)
        await session.commit()
        assert await repo.nearest(owner.id, doc.id, batch(0)) == [second, chunk]
        hybrid = await retrieve_hybrid(
            session, owner.id, doc.id, PassageQuery(query="graph", limit=2), batch(0)
        )
        assert hybrid.passages == [chunk, second]
        with pytest.raises(AppError) as denied:
            await retrieve_hybrid(
                session, uuid4(), doc.id, PassageQuery(query="graph"), batch(0)
            )
        assert denied.value.status_code == 404
        page.text = "changed source text"
        await session.flush()
        assert await repo.nearest(owner.id, doc.id, batch(1)) == [second]
    else:
        with pytest.raises(AppError) as error:
            await repo.nearest(owner.id, doc.id, batch())
        assert error.value.status_code == 503
    await session.delete(doc)
    await session.commit()
    assert await session.scalar(select(func.count()).select_from(DocumentVector)) == 0


def test_vector_lifecycle(migrated_database_url):
    asyncio.run(exercise(migrated_database_url, check_vectors))


@pytest.mark.parametrize(
    "case", ["wrong_model", "wrong_dimension", "zero", "nan", "partial"]
)
def test_invalid_index_preserves_existing_vectors(migrated_database_url, case):
    async def scenario(session, sessions, owner, doc):
        page, chunk = await seed(session, doc)
        repo = VectorRepository(session)
        await repo.replace(owner.id, doc.id, [chunk], batch())
        await session.commit()
        value = batch()
        if case == "wrong_model":
            value = EmbeddingBatch("other", value.dimensions, value.vectors, 1)
        elif case == "wrong_dimension":
            value = EmbeddingBatch(value.model, 2, ((1.0, 0.0),), 1)
        elif case in {"zero", "nan"}:
            vector = (0.0 if case == "zero" else float("nan"),) * EMBEDDING_DIMENSIONS
            value = EmbeddingBatch(value.model, value.dimensions, (vector,), 1)
        elif case == "partial":
            session.add(
                DocumentPage(
                    document_id=doc.id,
                    number=2,
                    text="Other",
                    chunks=[{"start": 0, "end": 5, "text": "Other"}],
                )
            )
            await session.commit()
        with pytest.raises(AppError):
            await repo.replace(owner.id, doc.id, [chunk], value)
        assert (
            await session.scalar(select(func.count()).select_from(DocumentVector)) == 1
        )

    asyncio.run(exercise(migrated_database_url, scenario))
