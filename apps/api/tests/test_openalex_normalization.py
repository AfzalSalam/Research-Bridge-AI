import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

from app.core.errors import AppError
from app.providers.base import ProviderRateLimit, RawProviderSearchResult
from app.providers.openalex.normalizer import (
    normalize_doi,
    normalize_search_result,
    reconstruct_abstract,
)
from app.services.discovery import classify_discovery_query

FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "openalex" / "works-representative.json"
)
RETRIEVED_AT = datetime(2026, 8, 1, 14, 30, tzinfo=UTC)


def load_records() -> list[dict[str, object]]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return payload["results"]


def raw_result(records: list[dict[str, object]]) -> RawProviderSearchResult:
    return RawProviderSearchResult(
        records=tuple(records),
        total_count=len(records),
        retrieved_at=RETRIEVED_AT,
        rate_limit=ProviderRateLimit(limit=1000, remaining=999),
        access_mode="api-key",
    )


def test_query_classification_supports_text_doi_and_openalex_ids() -> None:
    text = classify_discovery_query("  Human-centred   clinical AI  ")
    doi = classify_discovery_query("https://doi.org/10.1234/Example.01")
    work = classify_discovery_query("https://openalex.org/w1000000001/")

    assert (text.kind.value, text.value) == (
        "text",
        "Human-centred clinical AI",
    )
    assert (doi.kind.value, doi.value) == ("doi", "10.1234/example.01")
    assert (work.kind.value, work.value) == ("openalex-id", "W1000000001")


@pytest.mark.parametrize(
    "query",
    ["doi:not-a-doi", "https://doi.org/not-a-doi", "https://openalex.org/nope"],
)
def test_query_classification_rejects_explicit_malformed_identifiers(
    query: str,
) -> None:
    with pytest.raises(AppError) as captured:
        classify_discovery_query(query)

    assert captured.value.code == "invalid_discovery_query"
    assert captured.value.details[0]["field"] == "query"


def test_abstract_reconstruction_is_ordered_and_rejects_conflicts() -> None:
    assert reconstruct_abstract({"world": [1], "Hello": [0]}) == "Hello world"

    with pytest.raises(ValueError, match="conflicting"):
        reconstruct_abstract({"one": [0], "two": [0]})


def test_openalex_normalization_preserves_evidence_and_unknowns() -> None:
    normalized = normalize_search_result(raw_result(load_records()[:2]))

    assert normalized.skipped_count == 0
    assert len(normalized.papers) == 2
    first, second = normalized.papers
    assert first.openalex_id == "W1000000001"
    assert first.doi == "10.1234/rbai.2026.001"
    assert first.abstract == "Human-centred AI supports clinical decisions."
    assert first.evidence_strength == "full-abstract"
    assert first.authors[1].display_name == "José Álvarez"
    assert len(first.authors[0].institutions) == 2
    assert first.topics[0].score == 0.94
    assert second.authors[0].display_name == "李明"
    assert second.venue is None
    assert second.abstract is None
    assert second.evidence_strength == "title-only"


def test_partial_normalization_skips_invalid_and_retracted_records() -> None:
    normalized = normalize_search_result(raw_result(load_records()))

    assert len(normalized.papers) == 2
    assert normalized.skipped_count == 2
    assert normalized.invalid_count == 1
    assert normalized.excluded_count == 1
    assert any("required metadata was invalid" in item for item in normalized.warnings)
    assert any("retracted" in item for item in normalized.warnings)


def test_country_codes_are_trimmed_and_limited_to_ascii_iso_shape() -> None:
    records = load_records()[:1]
    work = cast(dict[str, Any], records[0])
    authorship = cast(list[dict[str, Any]], work["authorships"])[0]
    institutions = cast(list[dict[str, Any]], authorship["institutions"])
    institutions[0]["country_code"] = " gb "
    institutions[1]["country_code"] = "1X"

    normalized = normalize_search_result(raw_result(records))

    assert normalized.papers[0].authors[0].institutions[0].country_code == "GB"
    assert normalized.papers[0].authors[0].institutions[1].country_code is None


def test_missing_entity_ids_fall_back_to_the_supporting_work_source() -> None:
    records = load_records()[:1]
    work = cast(dict[str, Any], records[0])
    authorship = cast(list[dict[str, Any]], work["authorships"])[0]
    author = cast(dict[str, Any], authorship["author"])
    institution = cast(list[dict[str, Any]], authorship["institutions"])[0]
    author["id"] = None
    institution["id"] = None

    normalized = normalize_search_result(raw_result(records))
    normalized_author = normalized.papers[0].authors[0]

    assert normalized_author.source_url == "https://openalex.org/W1000000001"
    assert normalized_author.institutions[0].source_url == (
        "https://openalex.org/W1000000001"
    )


def test_distinct_openalex_ids_are_not_deduplicated_by_title_and_year() -> None:
    records = load_records()[:1]
    distinct_work = cast(dict[str, Any], deepcopy(records[0]))
    distinct_work["id"] = "https://openalex.org/W1000000099"
    distinct_work["doi"] = None
    records.append(distinct_work)

    normalized = normalize_search_result(raw_result(records))

    assert [paper.openalex_id for paper in normalized.papers] == [
        "W1000000001",
        "W1000000099",
    ]


def test_doi_normalization_never_accepts_arbitrary_urls() -> None:
    assert normalize_doi("DOI:10.1000/ABC") == "10.1000/abc"
    assert normalize_doi("https://example.org/10.1000/abc") is None
