from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from datetime import datetime
from typing import Literal, Protocol

from app.core.errors import AppError
from app.providers.base import (
    AcademicPaperProvider,
    AcademicProviderError,
    ClassifiedDiscoveryQuery,
    DiscoveryQueryKind,
    NormalizedProviderSearchResult,
    ProviderFailureKind,
)
from app.providers.openalex.normalizer import normalize_doi, normalize_search_result
from app.repositories.academic import AcademicRepository, StoredPaper
from app.schemas.discovery import (
    DiscoveredPaper,
    DiscoverySource,
    PaperAuthor,
    PaperDiscoveryRequest,
    PaperDiscoveryResponse,
    PaperInstitution,
    PaperTopic,
)
from app.services.search_cache import PaperSearchCache, SearchCacheKey

_OPENALEX_ID = re.compile(r"^W\d+$", re.IGNORECASE)
_OPENALEX_URL = re.compile(
    r"^https://openalex\.org/(?P<identifier>W\d+)/?$", re.IGNORECASE
)
_DOI_URL_PREFIXES = ("https://doi.org/", "http://doi.org/")


class PaperDiscoveryReader(Protocol):
    async def search(
        self, request: PaperDiscoveryRequest
    ) -> PaperDiscoveryResponse: ...


class PaperDiscoveryService:
    """Orchestrate deterministic provider retrieval, normalization, and storage."""

    def __init__(
        self,
        *,
        provider: AcademicPaperProvider,
        repository: AcademicRepository,
        cache: PaperSearchCache,
    ) -> None:
        self._provider = provider
        self._repository = repository
        self._cache = cache

    async def search(self, request: PaperDiscoveryRequest) -> PaperDiscoveryResponse:
        query = classify_discovery_query(request.query)
        cache_key = SearchCacheKey(
            provider=self._provider.name,
            query_kind=query.kind,
            query_value=query.value,
            limit=request.limit,
        )
        normalized = await self._cache.get(cache_key)
        cache_status: Literal["hit", "miss"] = "hit"
        if normalized is None:
            cache_status = "miss"
            try:
                raw = await self._provider.search_papers(query, request.limit)
            except AcademicProviderError as error:
                raise _public_provider_error(error) from error
            normalized = normalize_search_result(raw)
            if (
                not normalized.papers
                and normalized.invalid_count > 0
                and normalized.excluded_count == 0
            ):
                raise AppError(
                    code="academic_source_invalid_response",
                    message=(
                        "OpenAlex responded, but none of its records contained "
                        "the required publication evidence."
                    ),
                    status_code=502,
                )
            if normalized.skipped_count == 0 and not normalized.warnings:
                await self._cache.set(cache_key, normalized)

        stored = await self._repository.persist_papers(
            normalized.papers, retrieved_at=normalized.retrieved_at
        )
        return _response(
            query=query,
            normalized=normalized,
            stored=stored,
            cache_status=cache_status,
        )


def classify_discovery_query(value: str) -> ClassifiedDiscoveryQuery:
    normalized = " ".join(unicodedata.normalize("NFKC", value).split())
    url_match = _OPENALEX_URL.fullmatch(normalized)
    if url_match:
        identifier = url_match.group("identifier").upper()
        return ClassifiedDiscoveryQuery(
            kind=DiscoveryQueryKind.OPENALEX_ID,
            value=identifier,
            display_value=identifier,
        )
    if normalized.casefold().startswith("https://openalex.org/"):
        raise _invalid_query("Enter a valid OpenAlex Work URL or W identifier.")
    if _OPENALEX_ID.fullmatch(normalized):
        identifier = normalized.upper()
        return ClassifiedDiscoveryQuery(
            kind=DiscoveryQueryKind.OPENALEX_ID,
            value=identifier,
            display_value=identifier,
        )

    lowered = normalized.casefold()
    claims_doi = lowered.startswith("doi:") or lowered.startswith(_DOI_URL_PREFIXES)
    doi = normalize_doi(normalized)
    if doi:
        return ClassifiedDiscoveryQuery(
            kind=DiscoveryQueryKind.DOI, value=doi, display_value=doi
        )
    if claims_doi:
        raise _invalid_query("Enter a valid DOI such as 10.1000/example.")

    if len(normalized) < 3:
        raise _invalid_query("Describe a topic using at least 3 characters.")
    return ClassifiedDiscoveryQuery(
        kind=DiscoveryQueryKind.TEXT,
        value=normalized,
        display_value=normalized,
    )


def _invalid_query(message: str) -> AppError:
    return AppError(
        code="invalid_discovery_query",
        message="The paper query could not be classified.",
        status_code=422,
        details=[{"field": "query", "message": message, "type": "value_error.query"}],
    )


def _public_provider_error(error: AcademicProviderError) -> AppError:
    mapping = {
        ProviderFailureKind.AUTHENTICATION: (
            "academic_source_authentication_failed",
            "OpenAlex rejected the server's API credentials.",
            503,
        ),
        ProviderFailureKind.INVALID_RESPONSE: (
            "academic_source_invalid_response",
            "OpenAlex returned data that could not be safely validated.",
            502,
        ),
        ProviderFailureKind.NETWORK: (
            "academic_source_unreachable",
            "OpenAlex could not be reached within the bounded retry window.",
            503,
        ),
        ProviderFailureKind.RATE_LIMIT: (
            "academic_source_rate_limited",
            "OpenAlex has temporarily exhausted the configured request allowance.",
            503,
        ),
        ProviderFailureKind.REJECTED_REQUEST: (
            "academic_source_rejected_request",
            "OpenAlex rejected the normalized paper request.",
            502,
        ),
        ProviderFailureKind.TEMPORARY: (
            "academic_source_temporarily_unavailable",
            "OpenAlex remained unavailable after bounded retries.",
            503,
        ),
    }
    code, message, status_code = mapping[error.kind]
    details: list[Mapping[str, str]] = []
    if error.retry_after_seconds is not None:
        details.append(
            {
                "field": "source",
                "message": (
                    f"The provider reported a retry window of approximately "
                    f"{error.retry_after_seconds} seconds."
                ),
                "type": "provider.retry_after",
            }
        )
    return AppError(
        code=code, message=message, status_code=status_code, details=details
    )


def _abstract_excerpt(value: str | None) -> str | None:
    if value is None or len(value) <= 800:
        return value
    shortened = value[:797].rsplit(" ", 1)[0].rstrip()
    return f"{shortened}…"


def _paper_response(stored: StoredPaper, retrieved_at: datetime) -> DiscoveredPaper:
    paper = stored.value
    return DiscoveredPaper(
        id=stored.id,
        openalex_id=paper.openalex_id,
        doi=paper.doi,
        title=paper.title,
        publication_year=paper.publication_year,
        publication_date=paper.publication_date,
        work_type=paper.work_type,
        language=paper.language,
        venue=paper.venue,
        abstract_excerpt=_abstract_excerpt(paper.abstract),
        evidence_strength=paper.evidence_strength,
        source_url=paper.source_url,
        last_verified_at=retrieved_at,
        authors=[
            PaperAuthor(
                id=author.id,
                openalex_id=author.value.openalex_id,
                orcid=author.value.orcid,
                display_name=author.value.display_name,
                is_corresponding=author.value.is_corresponding,
                source_url=author.value.source_url,
                institutions=[
                    PaperInstitution(
                        id=institution.id,
                        openalex_id=institution.value.openalex_id,
                        ror_id=institution.value.ror_id,
                        display_name=institution.value.display_name,
                        country_code=institution.value.country_code,
                        city=institution.value.city,
                        source_url=institution.value.source_url,
                    )
                    for institution in author.institutions
                ],
            )
            for author in stored.authors
        ],
        topics=[
            PaperTopic(
                id=topic.id,
                openalex_id=topic.value.openalex_id,
                display_name=topic.value.display_name,
                score=topic.value.score,
            )
            for topic in stored.topics
        ],
    )


def _response(
    *,
    query: ClassifiedDiscoveryQuery,
    normalized: NormalizedProviderSearchResult,
    stored: tuple[StoredPaper, ...],
    cache_status: Literal["hit", "miss"],
) -> PaperDiscoveryResponse:
    status: Literal["complete", "partial", "empty"]
    if not stored:
        status = "empty"
    elif normalized.warnings or normalized.skipped_count:
        status = "partial"
    else:
        status = "complete"
    return PaperDiscoveryResponse(
        status=status,
        query=query.display_value,
        query_kind=query.kind.value,
        total_provider_results=normalized.total_count,
        returned_count=len(stored),
        skipped_count=normalized.skipped_count,
        warnings=list(normalized.warnings),
        source=DiscoverySource(
            retrieved_at=normalized.retrieved_at,
            access_mode=normalized.access_mode,
            cache_status=cache_status,
            rate_limit_remaining=normalized.rate_limit.remaining,
            rate_limit_reset_seconds=normalized.rate_limit.reset_seconds,
        ),
        papers=[_paper_response(paper, normalized.retrieved_at) for paper in stored],
    )
