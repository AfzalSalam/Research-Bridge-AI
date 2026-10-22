import json
from collections.abc import Iterator
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app
from app.providers.base import (
    ClassifiedDiscoveryQuery,
    ProviderRateLimit,
    RawProviderSearchResult,
)
from tests.auth_support import StaticAccessTokenVerifier, account_profile_payload

FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "openalex" / "works-representative.json"
)
RETRIEVED_AT = datetime(2026, 8, 1, 16, 0, tzinfo=UTC)


def repeated_author_records() -> list[dict[str, object]]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    records = deepcopy(payload["results"][:2])
    first_authorship = records[0]["authorships"][0]
    records[1]["authorships"].append(deepcopy(first_authorship))
    return records


class RepeatedAuthorProvider:
    name = "OpenAlex"

    async def search_papers(
        self, query: ClassifiedDiscoveryQuery, limit: int
    ) -> RawProviderSearchResult:
        records = repeated_author_records()
        return RawProviderSearchResult(
            records=tuple(records[:limit]),
            total_count=len(records),
            retrieved_at=RETRIEVED_AT,
            rate_limit=ProviderRateLimit(remaining=88, reset_seconds=3600),
            access_mode="api-key",
        )


@pytest.fixture
def mentor_client(migrated_database_url: str) -> Iterator[TestClient]:
    application = create_app(
        Settings(
            app_environment="test",
            backend_cors_origins="",
            database_url=migrated_database_url,
            log_level="CRITICAL",
        )
    )
    application.state.paper_provider_override = RepeatedAuthorProvider()
    application.state.auth_verifier_override = StaticAccessTokenVerifier(
        {
            "mentor-user-a": "supabase-mentor-a",
            "mentor-user-b": "supabase-mentor-b",
        }
    )
    with TestClient(application) as client:
        client.headers.update({"Authorization": "Bearer mentor-user-a"})
        assert client.put(
            "/api/v1/profile", json=account_profile_payload()
        ).status_code == 200
        yield client


def test_mentor_discovery_collapses_authors_and_preserves_evidence_boundaries(
    mentor_client: TestClient,
) -> None:
    response = mentor_client.post(
        "/api/v1/discovery/mentors",
        json={
            "query": "human-centred clinical decision support",
            "paperLimit": 20,
            "candidateLimit": 12,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ordering"] == "deterministic-evidence-policy"
    assert payload["policy"]["version"] == "placement-relevance-v1"
    assert sum(item["weight"] for item in payload["policy"]["weights"]) == 1
    assert payload["paperCount"] == 2
    assert payload["authorAppearanceCount"] == 4
    assert payload["derivedCandidateCount"] == 3
    assert payload["quality"]["duplicateCollapseRate"] == 0.25
    assert payload["quality"]["unsupportedClaimRate"] == 0

    candidate = payload["candidates"][0]
    assert candidate["displayName"] == "Mira Sen"
    assert candidate["supportingPaperCount"] == 2
    assert candidate["academicTitle"] is None
    assert candidate["currentInstitution"] is None
    assert candidate["availability"] == "unknown"
    assert candidate["lastVerifiedAt"] == "2026-08-01T16:00:00Z"
    assert "score" not in candidate
    assert candidate["supportingPapers"][0]["authorship"]["affiliationsAtPublication"]
    assert all(item["evidencePaperIds"] for item in candidate["contributions"])
    assert "current" in candidate["warnings"][0].casefold()
    assert payload["timing"]["retrievalAndPersistenceMs"] >= 0
    assert payload["timing"]["heuristicMs"] >= 0
    assert payload["timing"]["totalMs"] >= 0


def test_direct_doi_support_is_explicit_and_candidate_limit_is_applied(
    mentor_client: TestClient,
) -> None:
    response = mentor_client.post(
        "/api/v1/discovery/mentors",
        json={
            "query": "10.1234/rbai.2026.001",
            "paperLimit": 1,
            "candidateLimit": 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["queryKind"] == "doi"
    assert payload["returnedCount"] == 1
    query_evidence = next(
        item
        for item in payload["candidates"][0]["contributions"]
        if item["feature"] == "query-evidence"
    )
    assert query_evidence["value"] == 1
    assert query_evidence["evidencePaperIds"]


def test_invalid_weight_total_is_rejected_at_startup() -> None:
    with pytest.raises(ValidationError, match="weights must total one"):
        Settings(mentor_query_evidence_weight=0.5)


def test_mentor_discovery_requires_authentication_and_saved_profile(
    mentor_client: TestClient,
) -> None:
    mentor_client.headers.pop("Authorization")
    anonymous = mentor_client.post(
        "/api/v1/discovery/mentors", json={"query": "clinical support"}
    )
    assert anonymous.status_code == 401
    assert anonymous.json()["error"]["code"] == "authentication_required"

    missing_profile = mentor_client.post(
        "/api/v1/discovery/mentors",
        json={"query": "clinical support"},
        headers={"Authorization": "Bearer mentor-user-b"},
    )
    assert missing_profile.status_code == 409
    assert missing_profile.json()["error"]["code"] == "profile_required"


def test_mentor_matching_uses_each_authenticated_students_saved_facts(
    mentor_client: TestClient,
) -> None:
    query = {"query": "clinical decision support"}
    first = mentor_client.post("/api/v1/discovery/mentors", json=query)
    assert first.status_code == 200

    other_profile = {
        **account_profile_payload("Ben"),
        "researchInterests": ["radio astronomy"],
        "skills": ["telescope calibration"],
        "projectTitle": "Stellar observations",
        "projectSummary": (
            "Measured stellar brightness using a calibrated telescope and recorded "
            "the observations for a classroom astronomy project."
        ),
    }
    mentor_client.headers.update({"Authorization": "Bearer mentor-user-b"})
    assert mentor_client.put(
        "/api/v1/profile", json=other_profile
    ).status_code == 200
    second = mentor_client.post("/api/v1/discovery/mentors", json=query)
    assert second.status_code == 200
    assert first.json()["profileInputs"]["researchInterests"] == [
        "human-centred AI", "digital health"
    ]
    assert second.json()["profileInputs"] == {
        "researchInterests": ["radio astronomy"],
        "skills": ["telescope calibration"],
        "projectTitle": "Stellar observations",
    }
    first_alignment = next(
        item["value"]
        for item in first.json()["candidates"][0]["contributions"]
        if item["feature"] == "profile-alignment"
    )
    second_alignment = next(
        item["value"]
        for item in second.json()["candidates"][0]["contributions"]
        if item["feature"] == "profile-alignment"
    )
    assert first_alignment > second_alignment

    mentor_client.headers.update({"Authorization": "Bearer mentor-user-a"})
    reread = mentor_client.post("/api/v1/discovery/mentors", json=query)
    assert reread.json()["profileInputs"] == first.json()["profileInputs"]
