"""Fail-closed answer validation. Not exposed as a live generation endpoint."""

import asyncio
import json
from collections.abc import Sequence
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents.answer_prompts import ANSWER_SYSTEM, CONTEXT_SYSTEM, REVIEW_SYSTEM
from app.documents.contracts import PdfChunk, PdfPage
from app.documents.repository import DocumentRepository

MAX_RESPONSE_BYTES = 32_768


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Evidence(StrictModel):
    id: str
    page: int = Field(ge=1, le=100)
    start: int = Field(ge=0)
    end: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=1200)


class Citation(StrictModel):
    passage_id: str = Field(min_length=1, max_length=20)
    quote: str = Field(min_length=1, max_length=500)


class ProposedClaim(StrictModel):
    text: str = Field(min_length=1, max_length=1000)
    citations: list[Citation] = Field(min_length=1, max_length=3)


class Candidate(StrictModel):
    status: Literal["answer", "insufficient_evidence"]
    claims: list[ProposedClaim] = Field(max_length=5)

    @model_validator(mode="after")
    def consistent(self) -> "Candidate":
        if bool(self.claims) != (self.status == "answer"):
            raise ValueError("Answer status and claims must agree.")
        return self


class ClaimReview(StrictModel):
    index: int = Field(ge=0, le=4)
    verdict: Literal["supported", "unsupported", "uncertain"]


class SupportReview(StrictModel):
    addresses_question: bool
    claims: list[ClaimReview] = Field(min_length=1, max_length=5)


class PageCitation(StrictModel):
    page: int
    start: int
    end: int
    quote: str


class AnswerClaim(StrictModel):
    text: str
    citations: tuple[PageCitation, ...]


class AnswerResult(StrictModel):
    status: Literal["answer", "insufficient_evidence", "unavailable"]
    reason: Literal[
        "reviewed",
        "no_passages",
        "source_insufficient",
        "support_not_established",
        "not_configured",
        "invalid_provider_output",
        "provider_unavailable",
    ]
    claims: tuple[AnswerClaim, ...] = ()
    source_scope: Literal["retrieved_full_text_excerpts"] = (
        "retrieved_full_text_excerpts"
    )
    notice: str = (
        "Based on retrieved paper excerpts, not an exhaustive "
        "review of the whole paper."
    )


class AnswerProviderError(Exception):
    """Adapter must translate expected transport failures without private details."""


class AnswerProvider(Protocol):
    async def generate(self, system: str, payload: str) -> str: ...
    async def review(self, system: str, payload: str) -> str: ...


def evidence_bundle(
    pages: Sequence[PdfPage], passages: Sequence[PdfChunk]
) -> tuple[Evidence, ...]:
    if len(passages) > 10 or len({p.number for p in pages}) != len(pages):
        raise ValueError("Invalid evidence context.")
    source = {p.number: p.text for p in pages}
    seen = set()
    result: list[Evidence] = []
    for passage in passages:
        text = source.get(passage.page)
        identity = (passage.page, passage.start, passage.end)
        if (
            text is None
            or passage.end <= passage.start
            or passage.end > len(text)
            or text[passage.start : passage.end] != passage.text
            or not passage.text.strip()
        ):
            raise ValueError("Evidence does not match the stored source.")
        if identity not in seen:
            seen.add(identity)
            result.append(
                Evidence(
                    id=f"p{len(result)}",
                    page=passage.page,
                    start=passage.start,
                    end=passage.end,
                    text=passage.text,
                )
            )
    return tuple(result)


async def load_evidence(
    session: AsyncSession, owner: UUID, document: UUID, passages: Sequence[PdfChunk]
) -> tuple[Evidence, ...]:
    pages = await DocumentRepository(session).pages(owner, document)
    return evidence_bundle(
        [PdfPage(number=p.number, text=p.text) for p in pages], passages
    )


def checked_json(raw: str) -> str:
    if len(raw.encode("utf-8")) > MAX_RESPONSE_BYTES:
        raise ValueError("Provider output exceeds limit.")
    return raw


_LIGATURES = str.maketrans(
    {
        "\ufb00": "ff",
        "\ufb01": "fi",
        "\ufb02": "fl",
        "\ufb03": "ffi",
        "\ufb04": "ffl",
        "\ufb05": "st",
        "\ufb06": "st",
    }
)


def _quote_view(text: str) -> tuple[str, list[tuple[int, int]]]:
    chars: list[str] = []
    spans: list[tuple[int, int]] = []
    for index, char in enumerate(text):
        if char.isspace():
            if chars and chars[-1] == " ":
                spans[-1] = (spans[-1][0], index + 1)
                continue
            char = " "
        for expanded in char.translate(_LIGATURES):
            chars.append(expanded)
            spans.append((index, index + 1))
    return "".join(chars), spans


def quote_span(text: str, quote: str) -> tuple[int, int]:
    exact = text.find(quote)
    if exact >= 0:
        return exact, exact + len(quote)
    normalized, spans = _quote_view(text)
    needle, _ = _quote_view(quote)
    start = normalized.find(needle)
    if not needle.strip() or start < 0 or normalized.find(needle, start + 1) >= 0:
        raise ValueError("Quote absent or ambiguous.")
    end = start + len(needle)
    if (start > 0 and spans[start] == spans[start - 1]) or (
        end < len(spans) and spans[end - 1] == spans[end]
    ):
        raise ValueError("Quote cuts through a source character.")
    left, right = spans[start][0], spans[end - 1][1]
    if right - left > 500:
        raise ValueError("Source quote exceeds limit.")
    return left, right


def resolve(
    candidate: Candidate, evidence: tuple[Evidence, ...]
) -> tuple[AnswerClaim, ...]:
    sources = {item.id: item for item in evidence}
    resolved = []
    for claim in candidate.claims:
        if not claim.text.strip():
            raise ValueError("Blank answer claim.")
        citations = []
        for citation in claim.citations:
            passage = sources.get(citation.passage_id)
            if passage is None or not citation.quote.strip():
                raise ValueError("Invalid source reference.")
            offset, end = quote_span(passage.text, citation.quote)
            citations.append(
                PageCitation(
                    page=passage.page,
                    start=passage.start + offset,
                    end=passage.start + end,
                    quote=passage.text[offset:end],
                )
            )
        resolved.append(AnswerClaim(text=claim.text, citations=tuple(citations)))
    return tuple(resolved)


async def answer(
    question: str,
    evidence: tuple[Evidence, ...],
    provider: AnswerProvider | None = None,
) -> AnswerResult:
    if not question.strip() or len(question) > 500:
        raise ValueError("Question must contain 1-500 characters.")
    if len(evidence) > 10 or len({e.id for e in evidence}) != len(evidence):
        raise ValueError("Invalid evidence context.")
    if any(e.end - e.start != len(e.text) for e in evidence):
        raise ValueError("Invalid evidence offsets.")
    if not evidence:
        return AnswerResult(status="insufficient_evidence", reason="no_passages")
    if provider is None:
        return AnswerResult(status="unavailable", reason="not_configured")
    payload = json.dumps(
        {"question": question, "excerpts": [e.model_dump() for e in evidence]}
    )
    try:
        async with asyncio.timeout(60):
            candidate = Candidate.model_validate_json(
                checked_json(await provider.generate(ANSWER_SYSTEM, payload))
            )
            if candidate.status == "insufficient_evidence":
                return AnswerResult(
                    status="insufficient_evidence", reason="source_insufficient"
                )
            claims = resolve(candidate, evidence)
            base = {
                "question": question,
                "claims": [c.model_dump() for c in claims],
            }
            stages = (
                (REVIEW_SYSTEM, base),
                (
                    CONTEXT_SYSTEM,
                    {**base, "excerpts": [e.model_dump() for e in evidence]},
                ),
            )
            for instructions, data in stages:
                review = SupportReview.model_validate_json(
                    checked_json(await provider.review(instructions, json.dumps(data)))
                )
                if len(review.claims) != len(claims) or {
                    item.index for item in review.claims
                } != set(range(len(claims))):
                    raise ValueError("Incomplete support review.")
                if not review.addresses_question or any(
                    item.verdict != "supported" for item in review.claims
                ):
                    return AnswerResult(
                        status="insufficient_evidence", reason="support_not_established"
                    )
            return AnswerResult(status="answer", reason="reviewed", claims=claims)
    except (ValidationError, ValueError):
        return AnswerResult(status="unavailable", reason="invalid_provider_output")
    except (AnswerProviderError, TimeoutError):
        return AnswerResult(status="unavailable", reason="provider_unavailable")
