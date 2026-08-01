import json
import sqlite3
from collections.abc import Iterator
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.outreach.drafting import (
    CompositionPaperConnection,
    DraftProviderError,
    OutreachComposition,
    OutreachEvidencePackage,
)
from app.providers.base import (
    ClassifiedDiscoveryQuery,
    ProviderRateLimit,
    RawProviderSearchResult,
)

FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "openalex" / "works-representative.json"
)
RETRIEVED_AT = datetime(2026, 8, 1, 16, 0, tzinfo=UTC)
QUERY = "human-centred clinical decision support"


def repeated_author_records() -> list[dict[str, object]]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    records = deepcopy(payload["results"][:2])
    records[1]["authorships"].append(deepcopy(records[0]["authorships"][0]))
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


class ValidGenerator:
    name = "Fake structured provider"
    model = "test-model"

    async def generate(self, evidence: OutreachEvidencePackage) -> OutreachComposition:
        return OutreachComposition(
            subject="Question about your evidence-centred research",
            introduction=(
                f"I am {evidence.profile.name}, a {evidence.profile.program} "
                "student interested in responsible research software."
            ),
            student_fact_keys=["profile.name", "profile.program"],
            paper_connections=[
                CompositionPaperConnection(
                    paper_id=paper.id,
                    text=(
                        "The paper demonstrates a guaranteed result with your funded "
                        "lab opening."
                        if paper.evidence_strength == "title-only"
                        else f"I appreciated the evidence boundary in “{paper.title}” "
                        "and its connection to responsible decision support."
                    ),
                )
                for paper in evidence.papers
            ],
            ask=(
                "Would you be open to a brief conversation about whether a focused "
                "student contribution could be useful to your current research?"
            ),
        )


class BrokenGenerator:
    name = "Fake unavailable provider"
    model = "test-model"

    async def generate(self, evidence: OutreachEvidencePackage) -> OutreachComposition:
        raise DraftProviderError("provider-unavailable")


class UngroundedGenerator:
    name = "Fake ungrounded provider"
    model = "test-model"

    async def generate(self, evidence: OutreachEvidencePackage) -> OutreachComposition:
        return OutreachComposition(
            subject="Question about your funded lab opening",
            introduction=(
                "I am a student interested in evidence-centred research software "
                "and careful academic collaboration."
            ),
            student_fact_keys=["profile.name"],
            paper_connections=[
                CompositionPaperConnection(
                    paper_id=paper.id,
                    text=(
                        "I appreciated the evidence boundary in this selected paper "
                        "and would like to understand it more deeply."
                    ),
                )
                for paper in evidence.papers
            ],
            ask=(
                "Would you be open to a brief conversation about a focused student "
                "contribution to the work?"
            ),
        )


@pytest.fixture
def outreach_client(
    migrated_database_url: str,
) -> Iterator[tuple[TestClient, object]]:
    application = create_app(
        Settings(
            app_environment="test",
            backend_cors_origins="",
            database_url=migrated_database_url,
            log_level="CRITICAL",
        )
    )
    application.state.paper_provider_override = RepeatedAuthorProvider()
    with TestClient(application) as client:
        yield client, application


def _selected_candidate(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/discovery/mentors",
        json={"query": QUERY, "paperLimit": 20, "candidateLimit": 12},
    )
    response.raise_for_status()
    return next(
        candidate
        for candidate in response.json()["candidates"]
        if candidate["displayName"] == "Mira Sen"
    )


def _create_payload(
    candidate: dict[str, object], *, paper_count: int = 1
) -> dict[str, object]:
    papers = candidate["supportingPapers"]
    assert isinstance(papers, list)
    return {
        "query": QUERY,
        "mentorId": candidate["id"],
        "paperIds": [paper["id"] for paper in papers[:paper_count]],
        "generationPreference": "deterministic",
    }


def test_deterministic_draft_is_grounded_persisted_and_never_sendable(
    outreach_client: tuple[TestClient, object],
) -> None:
    client, _ = outreach_client
    candidate = _selected_candidate(client)

    response = client.post(
        "/api/v1/outreach/drafts", json=_create_payload(candidate, paper_count=2)
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["mentorId"] == candidate["id"]
    assert payload["recipientContact"] is None
    assert payload["canSend"] is False
    assert payload["generation"] == {
        "mode": "deterministic",
        "provider": None,
        "model": None,
        "promptVersion": None,
        "templateVersion": "outreach-template.v1",
        "fallbackReason": "deterministic-requested",
    }
    assert payload["draftVersion"] == 1
    assert payload["createdAt"].endswith("Z")
    assert payload["updatedAt"].endswith("Z")
    assert payload["revisions"][0]["createdAt"].endswith("Z")
    assert payload["evidenceMapStatus"] == "verified-generated"
    assert len(payload["selectedPapers"]) == 2
    assert all(claim["references"] for claim in payload["claimEvidence"])
    assert "only title-level metadata" in payload["body"]
    assert "cannot be sent" in " ".join(payload["uncertaintyWarnings"])
    assert all(
        "send" not in str(getattr(route, "path", "")) for route in client.app.routes
    )


def test_edits_append_revisions_and_reject_stale_versions(
    outreach_client: tuple[TestClient, object], migrated_database_url: str
) -> None:
    client, _ = outreach_client
    created = client.post(
        "/api/v1/outreach/drafts",
        json=_create_payload(_selected_candidate(client)),
    ).json()
    update = {
        "subject": "Edited evidence-grounded research question",
        "body": created["body"]
        + "\n\nI have reviewed this additional sentence against my saved profile.",
        "expectedVersion": 1,
    }

    saved = client.put(f"/api/v1/outreach/drafts/{created['id']}", json=update)
    stale = client.put(f"/api/v1/outreach/drafts/{created['id']}", json=update)
    reread = client.get(f"/api/v1/outreach/drafts/{created['id']}")

    assert saved.status_code == 200
    assert saved.json()["draftVersion"] == 2
    assert saved.json()["evidenceMapStatus"] == "manual-edit-needs-review"
    assert [item["version"] for item in saved.json()["revisions"]] == [1, 2]
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "draft_version_conflict"
    assert reread.json()["subject"] == update["subject"]

    database_path = migrated_database_url.removeprefix("sqlite+aiosqlite:///")
    with sqlite3.connect(database_path) as connection:
        revision_count = connection.execute(
            "SELECT COUNT(*) FROM outreach_draft_revisions"
        ).fetchone()
    assert revision_count == (2,)


def test_invalid_researcher_and_paper_ids_are_rejected(
    outreach_client: tuple[TestClient, object],
) -> None:
    client, _ = outreach_client
    candidate = _selected_candidate(client)
    payload = _create_payload(candidate)

    unknown_mentor = client.post(
        "/api/v1/outreach/drafts",
        json={**payload, "mentorId": str(UUID(int=9))},
    )
    unknown_paper = client.post(
        "/api/v1/outreach/drafts",
        json={**payload, "paperIds": [str(UUID(int=10))]},
    )

    assert unknown_mentor.status_code == 422
    assert unknown_mentor.json()["error"]["code"] == "outreach_mentor_not_found"
    assert unknown_paper.status_code == 422
    assert unknown_paper.json()["error"]["code"] == "outreach_paper_not_found"


def test_valid_structured_generation_uses_model_but_replaces_title_only_prose(
    outreach_client: tuple[TestClient, object],
) -> None:
    client, application = outreach_client
    application.state.outreach_generator_override = ValidGenerator()
    candidate = _selected_candidate(client)
    payload = {
        **_create_payload(candidate, paper_count=2),
        "generationPreference": "auto",
    }

    response = client.post("/api/v1/outreach/drafts", json=payload)

    assert response.status_code == 201
    draft = response.json()
    assert draft["generation"]["mode"] == "llm"
    assert draft["generation"]["provider"] == "Fake structured provider"
    assert draft["generation"]["promptVersion"] == "outreach-grounded.v1"
    assert "funded lab opening" not in draft["body"]
    assert "only title-level metadata" in draft["body"]


def test_provider_failure_falls_back_without_exposing_provider_details(
    outreach_client: tuple[TestClient, object],
) -> None:
    client, application = outreach_client
    application.state.outreach_generator_override = BrokenGenerator()
    candidate = _selected_candidate(client)
    payload = {**_create_payload(candidate), "generationPreference": "auto"}

    response = client.post("/api/v1/outreach/drafts", json=payload)

    assert response.status_code == 201
    generation = response.json()["generation"]
    assert generation["mode"] == "deterministic"
    assert generation["provider"] is None
    assert generation["model"] is None
    assert generation["fallbackReason"] == "provider-unavailable"


def test_unsupported_provider_claim_fails_grounding_and_uses_safe_fallback(
    outreach_client: tuple[TestClient, object],
) -> None:
    client, application = outreach_client
    application.state.outreach_generator_override = UngroundedGenerator()
    candidate = _selected_candidate(client)
    payload = {**_create_payload(candidate), "generationPreference": "auto"}

    response = client.post("/api/v1/outreach/drafts", json=payload)

    assert response.status_code == 201
    draft = response.json()
    assert draft["generation"]["mode"] == "deterministic"
    assert draft["generation"]["fallbackReason"] == "grounding-check-failed"
    assert "funded lab opening" not in draft["subject"]
