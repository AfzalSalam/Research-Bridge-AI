from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import asdict
from typing import Any

from pydantic import ValidationError

from app.providers.base import (
    NormalizedAuthor,
    NormalizedInstitution,
    NormalizedPaper,
    NormalizedProviderSearchResult,
    NormalizedTopic,
    RawProviderSearchResult,
)
from app.providers.openalex.models import (
    OpenAlexAuthor,
    OpenAlexInstitution,
    OpenAlexTopic,
    OpenAlexWork,
)

_OPENALEX_ID = re.compile(r"^(?P<prefix>[WAIT])(?P<number>\d+)$", re.IGNORECASE)
_ORCID = re.compile(r"^\d{4}-\d{4}-\d{4}-[\dX]{4}$", re.IGNORECASE)
_MAX_ABSTRACT_POSITION = 20_000
_MAX_ABSTRACT_LENGTH = 50_000


def display_text(value: str, *, maximum: int) -> str:
    """Preserve Unicode spelling while removing unstable whitespace."""

    normalized = unicodedata.normalize("NFKC", value)
    collapsed = " ".join(normalized.split())
    if not collapsed or len(collapsed) > maximum:
        raise ValueError("provider text is empty or exceeds its allowed length")
    return collapsed


def normalized_key(value: str, *, maximum: int) -> str:
    return display_text(value, maximum=maximum).casefold()


def normalize_openalex_id(value: str | None, prefix: str) -> str | None:
    if value is None:
        return None
    candidate = value.strip().rstrip("/").rsplit("/", 1)[-1].upper()
    match = _OPENALEX_ID.fullmatch(candidate)
    if match is None or match.group("prefix").upper() != prefix:
        return None
    return candidate


def normalize_doi(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = unicodedata.normalize("NFKC", value).strip()
    lowered = candidate.casefold()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if lowered.startswith(prefix):
            candidate = candidate[len(prefix) :]
            break
    candidate = candidate.strip().casefold()
    if not candidate.startswith("10.") or "/" not in candidate or len(candidate) > 255:
        return None
    return candidate


def normalize_orcid(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip().rstrip("/").rsplit("/", 1)[-1].upper()
    return candidate if _ORCID.fullmatch(candidate) else None


def normalize_ror(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip().rstrip("/").rsplit("/", 1)[-1].casefold()
    return candidate if 7 <= len(candidate) <= 16 else None


def stable_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def reconstruct_abstract(index: dict[str, list[int]] | None) -> str | None:
    if not index:
        return None
    positions: dict[int, str] = {}
    for raw_token, raw_positions in index.items():
        token = display_text(raw_token, maximum=200)
        for position in raw_positions:
            if isinstance(position, bool) or not isinstance(position, int):
                raise ValueError("abstract position must be an integer")
            if position < 0 or position > _MAX_ABSTRACT_POSITION:
                raise ValueError("abstract position is outside the allowed range")
            previous = positions.get(position)
            if previous is not None and previous != token:
                raise ValueError("abstract contains conflicting token positions")
            positions[position] = token
    if not positions:
        return None
    abstract = " ".join(token for _, token in sorted(positions.items()))
    if len(abstract) > _MAX_ABSTRACT_LENGTH:
        raise ValueError("abstract exceeds the allowed length")
    return abstract


def _normalize_institution(
    raw: OpenAlexInstitution,
    *,
    fallback_source_url: str,
) -> NormalizedInstitution | None:
    if raw.display_name is None:
        return None
    try:
        display_name = display_text(raw.display_name, maximum=240)
    except ValueError:
        return None
    openalex_id = normalize_openalex_id(raw.id, "I")
    ror_id = normalize_ror(raw.ror)
    country_candidate = raw.country_code.strip().upper() if raw.country_code else ""
    country_code = (
        country_candidate
        if re.fullmatch(r"[A-Z]{2}", country_candidate) is not None
        else None
    )
    city = None
    if raw.geo and raw.geo.city:
        try:
            city = display_text(raw.geo.city, maximum=120)
        except ValueError:
            city = None
    source_url = (
        f"https://openalex.org/{openalex_id}" if openalex_id else fallback_source_url
    )
    content = {
        "openalex_id": openalex_id,
        "ror_id": ror_id,
        "display_name": display_name,
        "country_code": country_code,
        "city": city,
    }
    return NormalizedInstitution(
        openalex_id=openalex_id,
        ror_id=ror_id,
        display_name=display_name,
        normalized_name=normalized_key(display_name, maximum=240),
        country_code=country_code,
        city=city,
        source_url=source_url,
        content_hash=stable_hash(content),
    )


def _normalize_author(
    raw: OpenAlexAuthor,
    *,
    is_corresponding: bool | None,
    institutions: list[OpenAlexInstitution],
    fallback_source_url: str,
) -> NormalizedAuthor | None:
    if raw.display_name is None:
        return None
    try:
        display_name = display_text(raw.display_name, maximum=240)
    except ValueError:
        return None
    openalex_id = normalize_openalex_id(raw.id, "A")
    normalized_institutions: list[NormalizedInstitution] = []
    seen: set[tuple[str | None, str | None, str, str | None]] = set()
    for institution in institutions:
        normalized = _normalize_institution(
            institution, fallback_source_url=fallback_source_url
        )
        if normalized is None:
            continue
        identity = (
            normalized.openalex_id,
            normalized.ror_id,
            normalized.normalized_name,
            normalized.country_code,
        )
        if identity in seen:
            continue
        seen.add(identity)
        normalized_institutions.append(normalized)
    source_url = (
        f"https://openalex.org/{openalex_id}" if openalex_id else fallback_source_url
    )
    content = {
        "openalex_id": openalex_id,
        "orcid": normalize_orcid(raw.orcid),
        "display_name": display_name,
    }
    return NormalizedAuthor(
        openalex_id=openalex_id,
        orcid=normalize_orcid(raw.orcid),
        display_name=display_name,
        normalized_name=normalized_key(display_name, maximum=240),
        source_url=source_url,
        is_corresponding=is_corresponding,
        institutions=tuple(normalized_institutions),
        content_hash=stable_hash(content),
    )


def _normalize_topic(raw: OpenAlexTopic) -> NormalizedTopic | None:
    if raw.display_name is None:
        return None
    try:
        display_name = display_text(raw.display_name, maximum=160)
    except ValueError:
        return None
    return NormalizedTopic(
        openalex_id=normalize_openalex_id(raw.id, "T"),
        display_name=display_name,
        normalized_name=normalized_key(display_name, maximum=160),
        score=raw.score,
    )


def _normalize_work(raw: OpenAlexWork) -> tuple[NormalizedPaper, list[str]]:
    warnings: list[str] = []
    openalex_id = normalize_openalex_id(raw.id, "W")
    if openalex_id is None or raw.title is None or raw.publication_year is None:
        raise ValueError("work is missing a usable ID, title, or publication year")
    title = display_text(raw.title, maximum=20_000)
    try:
        abstract = reconstruct_abstract(raw.abstract_inverted_index)
    except ValueError:
        abstract = None
        warnings.append(
            f"{openalex_id} had an invalid abstract index; "
            "only title-level evidence is shown."
        )
    venue = None
    if raw.primary_location and raw.primary_location.source:
        raw_venue = raw.primary_location.source.display_name
        if raw_venue:
            try:
                venue = display_text(raw_venue, maximum=240)
            except ValueError:
                warnings.append(f"{openalex_id} had unusable venue metadata.")

    authors: list[NormalizedAuthor] = []
    seen_authors: set[tuple[str | None, str | None, str]] = set()
    work_source_url = f"https://openalex.org/{openalex_id}"
    for authorship in raw.authorships:
        author = _normalize_author(
            authorship.author,
            is_corresponding=authorship.is_corresponding,
            institutions=authorship.institutions,
            fallback_source_url=work_source_url,
        )
        if author is None:
            warnings.append(f"{openalex_id} contained an unusable authorship.")
            continue
        author_identity = (author.openalex_id, author.orcid, author.normalized_name)
        if author_identity in seen_authors:
            continue
        seen_authors.add(author_identity)
        authors.append(author)

    topics: list[NormalizedTopic] = []
    seen_topics: set[tuple[str | None, str]] = set()
    for raw_topic in raw.topics:
        topic = _normalize_topic(raw_topic)
        if topic is None:
            continue
        topic_identity = (topic.openalex_id, topic.normalized_name)
        if topic_identity in seen_topics:
            continue
        seen_topics.add(topic_identity)
        topics.append(topic)

    work_type = None
    if raw.type:
        try:
            work_type = display_text(raw.type, maximum=40).casefold()
        except ValueError:
            warnings.append(f"{openalex_id} had unusable work-type metadata.")
    language = raw.language.casefold()[:8] if raw.language else None
    paper_content = {
        "openalex_id": openalex_id,
        "doi": normalize_doi(raw.doi),
        "title": title,
        "publication_year": raw.publication_year,
        "publication_date": raw.publication_date,
        "work_type": work_type,
        "language": language,
        "is_retracted": raw.is_retracted,
        "venue": venue,
        "abstract": abstract,
        "authors": [asdict(author) for author in authors],
        "topics": [asdict(topic) for topic in topics],
    }
    return (
        NormalizedPaper(
            openalex_id=openalex_id,
            doi=normalize_doi(raw.doi),
            title=title,
            normalized_title=normalized_key(title, maximum=20_000)[:500],
            publication_year=raw.publication_year,
            publication_date=raw.publication_date,
            work_type=work_type,
            language=language,
            is_retracted=raw.is_retracted,
            venue=venue,
            abstract=abstract,
            evidence_strength="full-abstract" if abstract else "title-only",
            source_url=work_source_url,
            authors=tuple(authors),
            topics=tuple(topics),
            content_hash=stable_hash(paper_content),
        ),
        warnings,
    )


def normalize_search_result(
    raw_result: RawProviderSearchResult,
) -> NormalizedProviderSearchResult:
    papers: list[NormalizedPaper] = []
    warnings: list[str] = []
    skipped_count = 0
    invalid_count = 0
    excluded_count = 0
    seen_openalex_ids: set[str] = set()
    seen_dois: set[str] = set()

    for index, record in enumerate(raw_result.records):
        try:
            raw_work = OpenAlexWork.model_validate(record)
            paper, record_warnings = _normalize_work(raw_work)
        except (ValidationError, ValueError):
            skipped_count += 1
            invalid_count += 1
            warnings.append(
                f"OpenAlex record {index + 1} was skipped because required "
                "metadata was invalid."
            )
            continue
        if paper.is_retracted:
            skipped_count += 1
            excluded_count += 1
            warnings.append(
                f"{paper.openalex_id} was excluded because OpenAlex marks it "
                "as retracted."
            )
            continue
        duplicate = paper.openalex_id in seen_openalex_ids or (
            paper.doi is not None and paper.doi in seen_dois
        )
        if duplicate:
            skipped_count += 1
            excluded_count += 1
            warnings.append(f"Duplicate work {paper.openalex_id} was removed.")
            continue
        seen_openalex_ids.add(paper.openalex_id)
        if paper.doi:
            seen_dois.add(paper.doi)
        papers.append(paper)
        warnings.extend(record_warnings)

    return NormalizedProviderSearchResult(
        papers=tuple(papers),
        total_count=raw_result.total_count,
        skipped_count=skipped_count,
        invalid_count=invalid_count,
        excluded_count=excluded_count,
        warnings=tuple(warnings),
        retrieved_at=raw_result.retrieved_at,
        rate_limit=raw_result.rate_limit,
        access_mode=raw_result.access_mode,
    )
