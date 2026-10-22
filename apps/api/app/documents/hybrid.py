"""Bounded hybrid retrieval; callers supply an already budgeted query embedding.

No external calls or generated answers. Rank fusion is not a confidence score.
"""

from collections.abc import Mapping, Sequence
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents.contracts import PdfChunk
from app.documents.embeddings import EmbeddingBatch
from app.documents.repository import DocumentRepository
from app.documents.retrieval import PassageQuery, retrieve
from app.documents.vectors import VectorRepository


class HybridResult(BaseModel):
    document_id: UUID
    passages: list[PdfChunk]
    notice: str = (
        "Keyword and semantic matches are source excerpts, not proof that the "
        "paper answers your question."
    )


def fuse(
    rankings: Sequence[Sequence[PdfChunk]],
    page_text: Mapping[int, str],
    *,
    limit: int,
) -> list[PdfChunk]:
    """Equal-weight reciprocal ranks with fixed k=60 and stable source-order ties."""
    if not 1 <= limit <= 10:
        raise ValueError("Passage limit must be between 1 and 10.")
    scores: dict[tuple[int, int, int], float] = {}
    chunks: dict[tuple[int, int, int], PdfChunk] = {}
    for ranking in rankings:
        seen: set[tuple[int, int, int]] = set()
        rank = 0
        for chunk in ranking:
            key = (chunk.page, chunk.start, chunk.end)
            source = page_text.get(chunk.page)
            if (
                key in seen
                or source is None
                or chunk.end <= chunk.start
                or chunk.end > len(source)
                or source[chunk.start : chunk.end] != chunk.text
            ):
                continue
            seen.add(key)
            rank += 1
            scores[key] = scores.get(key, 0.0) + 1.0 / (60 + rank)
            chunks[key] = chunk
    selected: list[PdfChunk] = []
    for key in sorted(scores, key=lambda key: (-scores[key], key)):
        chunk = chunks[key]
        if any(
            item.page == chunk.page
            and item.start <= chunk.start
            and chunk.end <= item.end
            for item in selected
        ):
            continue
        selected.append(chunk)
        if len(selected) == limit:
            break
    return selected


async def retrieve_hybrid(
    session: AsyncSession,
    owner: UUID,
    document: UUID,
    request: PassageQuery,
    query_embedding: EmbeddingBatch,
) -> HybridResult:
    # Ownership/readiness precedes both searches. Each repository also checks it.
    await DocumentRepository(session).pages(owner, document)
    lexical = await retrieve(
        session, owner, document, request.model_copy(update={"limit": 10})
    )
    semantic = await VectorRepository(session).nearest(
        owner, document, query_embedding, limit=10
    )
    # Recheck source text after retrieval; forged or stale offsets never escape.
    pages = await DocumentRepository(session).pages(owner, document)
    return HybridResult(
        document_id=document,
        passages=fuse(
            [lexical.passages, semantic],
            {page.number: page.text for page in pages},
            limit=request.limit,
        ),
    )
