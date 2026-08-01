import json
import sqlite3
from collections.abc import Iterator
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.providers.base import (
    AcademicProviderError,
    ClassifiedDiscoveryQuery,
    ProviderFailureKind,
    ProviderRateLimit,
    RawProviderSearchResult,
)

FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "openalex" / "works-representative.json"
)
RETRIEVED_AT = datetime(2026, 8, 1, 16, 0, tzinfo=UTC)


def fixture_records() -> list[dict[str, object]]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return payload["results"]


class FixtureProvider:
    name = "OpenAlex"

    def __init__(self, records: list[dict[str, object]]) -> None:
        self.records = records
        self.calls: list[tuple[ClassifiedDiscoveryQuery, int]] = []

    async def search_papers(
        self, query: ClassifiedDiscoveryQuery, limit: int
    ) -> RawProviderSearchResult:
        self.calls.append((query, limit))
        return RawProviderSearchResult(
            records=tuple(self.records),
            total_count=len(self.records),
            retrieved_at=RETRIEVED_AT,
            rate_limit=ProviderRateLimit(remaining=88, reset_seconds=3600),
            access_mode="api-key",
        )


@pytest.fixture
def discovery_client(
    migrated_database_url: str,
) -> Iterator[tuple[TestClient, FixtureProvider]]:
    provider = FixtureProvider(fixture_records()[:2])
    application = create_app(
        Settings(
            app_environment="test",
            backend_cors_origins="http://localhost:3000",
            database_url=migrated_database_url,
            log_level="CRITICAL",
        )
    )
    application.state.paper_provider_override = provider
    with TestClient(application) as client:
        yield client, provider


def test_live_discovery_persists_evidence_and_reuses_the_cache(
    discovery_client: tuple[TestClient, FixtureProvider],
    migrated_database_url: str,
) -> None:
    client, provider = discovery_client
    body = {"query": "human-centred clinical AI", "limit": 12}

    first = client.post("/api/v1/discovery/papers", json=body)
    second = client.post("/api/v1/discovery/papers", json=body)

    assert first.status_code == 200
    assert first.json()["status"] == "complete"
    assert first.json()["source"]["cacheStatus"] == "miss"
    assert second.json()["source"]["cacheStatus"] == "hit"
    assert len(provider.calls) == 1
    paper = first.json()["papers"][0]
    assert paper["evidenceStrength"] == "full-abstract"
    assert paper["authors"][1]["displayName"] == "José Álvarez"
    assert len(paper["authors"][0]["institutions"]) == 2
    assert paper["topics"][0]["score"] == 0.94
    assert first.json()["ordering"] == "openalex-provider"

    database_path = migrated_database_url.removeprefix("sqlite+aiosqlite:///")
    with sqlite3.connect(database_path) as connection:
        counts = connection.execute(
            "SELECT "
            "(SELECT COUNT(*) FROM papers), "
            "(SELECT COUNT(*) FROM authors), "
            "(SELECT COUNT(*) FROM institutions), "
            "(SELECT COUNT(*) FROM paper_author_institutions), "
            "(SELECT COUNT(*) FROM provenance_records)"
        ).fetchone()
    assert counts == (2, 3, 2, 3, 7)


def test_partial_provider_data_preserves_valid_papers(
    migrated_database_url: str,
) -> None:
    provider = FixtureProvider(fixture_records())
    application = create_app(
        Settings(
            app_environment="test",
            backend_cors_origins="",
            database_url=migrated_database_url,
            log_level="CRITICAL",
        )
    )
    application.state.paper_provider_override = provider

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/discovery/papers",
            json={"query": "responsible clinical AI", "limit": 10},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "partial"
    assert response.json()["returnedCount"] == 2
    assert response.json()["skippedCount"] == 2
    assert len(response.json()["warnings"]) == 2


def test_sparse_refresh_does_not_erase_previously_verified_paper_fields(
    migrated_database_url: str,
) -> None:
    first_record = fixture_records()[0]
    sparse_record = deepcopy(first_record)
    sparse_record["doi"] = None
    sparse_record["abstract_inverted_index"] = None
    sparse_record["primary_location"] = None

    for record in (first_record, sparse_record):
        application = create_app(
            Settings(
                app_environment="test",
                backend_cors_origins="",
                database_url=migrated_database_url,
                log_level="CRITICAL",
            )
        )
        application.state.paper_provider_override = FixtureProvider([record])
        with TestClient(application) as client:
            response = client.post(
                "/api/v1/discovery/papers",
                json={"query": "human-centred clinical AI", "limit": 1},
            )
            response.raise_for_status()

    database_path = migrated_database_url.removeprefix("sqlite+aiosqlite:///")
    with sqlite3.connect(database_path) as connection:
        stored = connection.execute(
            "SELECT doi, abstract, venue, evidence_strength FROM papers"
        ).fetchone()

    assert stored == (
        "10.1234/rbai.2026.001",
        "Human-centred AI supports clinical decisions.",
        "Journal of Responsible Health AI",
        "abstract",
    )


def test_provider_rate_limit_uses_a_safe_structured_error(
    migrated_database_url: str,
) -> None:
    class RateLimitedProvider:
        name = "OpenAlex"

        async def search_papers(
            self, query: ClassifiedDiscoveryQuery, limit: int
        ) -> RawProviderSearchResult:
            raise AcademicProviderError(
                ProviderFailureKind.RATE_LIMIT,
                retryable=True,
                retry_after_seconds=120,
            )

    application = create_app(
        Settings(
            app_environment="test",
            backend_cors_origins="",
            database_url=migrated_database_url,
            log_level="CRITICAL",
        )
    )
    application.state.paper_provider_override = RateLimitedProvider()
    with TestClient(application) as client:
        response = client.post(
            "/api/v1/discovery/papers",
            headers={"X-Request-ID": "openalex-rate-test"},
            json={"query": "clinical information retrieval"},
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "academic_source_rate_limited"
    assert response.json()["error"]["requestId"] == "openalex-rate-test"
    assert response.json()["error"]["details"][0]["type"] == ("provider.retry_after")
    assert "api_key" not in response.text


def test_invalid_identifier_returns_a_field_level_error(
    discovery_client: tuple[TestClient, FixtureProvider],
) -> None:
    client, provider = discovery_client
    response = client.post("/api/v1/discovery/papers", json={"query": "doi:not-valid"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_discovery_query"
    assert response.json()["error"]["details"][0]["field"] == "query"
    assert provider.calls == []
