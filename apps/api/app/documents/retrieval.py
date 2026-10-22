"""Deterministic passage retrieval; matching is not proof an answer exists."""

import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents.contracts import PdfChunk
from app.documents.repository import DocumentRepository

STOP_WORDS = frozenset(
    [
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "what",
        "which",
        "how",
        "why",
        "when",
        "where",
        "does",
        "do",
        "did",
        "this",
        "that",
        "of",
        "in",
        "on",
        "to",
        "for",
        "and",
        "or",
        "with",
        "paper",
        "study",
        "explain",
        "describe",
    ]
)


class PassageQuery(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=5, ge=1, le=10)


class PassageResult(BaseModel):
    document_id: UUID
    status: Literal["matches", "no_matches"]
    engine: Literal["postgresql_fts", "lexical_fallback"]
    passages: list[PdfChunk]
    notice: str = (
        "Matching passages are source excerpts, not an answer or proof of support."
    )


def keywords(query: str) -> list[str]:
    return list(
        dict.fromkeys(
            word
            for word in re.findall(r"[^\W_]+", query.casefold())
            if len(word) > 1 and word not in STOP_WORDS
        )
    )[:24]


async def retrieve(
    session: AsyncSession, owner: UUID, document: UUID, request: PassageQuery
) -> PassageResult:
    # This also enforces ready status; bounded to 100 pages / 500k extracted chars.
    pages = await DocumentRepository(session).pages(owner, document)
    postgres = session.get_bind().dialect.name == "postgresql"
    engine: Literal["postgresql_fts", "lexical_fallback"] = (
        "postgresql_fts" if postgres else "lexical_fallback"
    )
    terms = keywords(request.query)
    candidates: list[tuple[float, PdfChunk]] = []
    if terms and postgres:
        rows = await session.execute(
            text("""
            WITH q AS (SELECT websearch_to_tsquery('simple', :query) AS value)
            SELECT p.number, c.value->>'start' AS start, c.value->>'end' AS end,
                   c.value->>'text' AS excerpt,
                   ts_rank_cd(to_tsvector('simple', c.value->>'text'), q.value) AS rank
            FROM document_pages p
            JOIN research_documents d ON d.id = p.document_id
            CROSS JOIN q
            CROSS JOIN LATERAL json_array_elements(p.chunks) c(value)
            WHERE p.document_id = :document AND d.owner_id = :owner
              AND d.status = 'ready'
              AND to_tsvector('simple', p.text) @@ q.value
              AND to_tsvector('simple', c.value->>'text') @@ q.value
            ORDER BY rank DESC, p.number, (c.value->>'start')::integer
        """),
            {"query": " OR ".join(terms), "document": document, "owner": owner},
        )
        for row in rows.mappings():
            candidates.append(
                (
                    float(row["rank"]),
                    PdfChunk(
                        page=row["number"],
                        start=int(row["start"]),
                        end=int(row["end"]),
                        text=row["excerpt"],
                    ),
                )
            )
    elif terms:
        for page in pages:
            for raw in page.chunks:
                chunk = PdfChunk(page=page.number, **raw)
                overlap = len(set(terms) & set(keywords(chunk.text)))
                if overlap:
                    candidates.append((float(overlap), chunk))
        candidates.sort(key=lambda item: (-item[0], item[1].page, item[1].start))
    page_text = {page.number: page.text for page in pages}
    selected: list[PdfChunk] = []
    for _, chunk in candidates:
        # Never expose a citation whose offsets do not reproduce the stored page.
        if page_text.get(chunk.page, "")[chunk.start : chunk.end] != chunk.text:
            continue
        if any(
            previous.page == chunk.page
            and min(previous.end, chunk.end) > max(previous.start, chunk.start)
            for previous in selected
        ):
            continue
        selected.append(chunk)
        if len(selected) == request.limit:
            break
    return PassageResult(
        document_id=document,
        status="matches" if selected else "no_matches",
        engine=engine,
        passages=selected,
    )
