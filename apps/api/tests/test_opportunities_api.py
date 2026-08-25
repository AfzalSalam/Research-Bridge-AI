from collections.abc import Iterator
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.providers.opportunities import (
    OpportunityProviderError,
    OpportunityProviderFailureKind,
    OpportunitySource,
    RawOpportunityBoard,
    RawOpportunityRecord,
)
from tests.auth_support import StaticAccessTokenVerifier

FIXED_TIME = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


class OpportunityFixtureProvider:
    async def fetch_board(self, source: OpportunitySource) -> RawOpportunityBoard:
        if source.key == "constructorknowledgelabs":
            raise OpportunityProviderError(
                OpportunityProviderFailureKind.NETWORK, retryable=True
            )
        return RawOpportunityBoard(
            source=source,
            records=(
                RawOpportunityRecord(
                    id=7366273,
                    title="Research Internship, Robotics",
                    updated_at=datetime(2026, 7, 30, 16, 0, tzinfo=UTC),
                    location="Seattle, WA",
                    absolute_url=(
                        "https://job-boards.greenhouse.io/"
                        "thealleninstitute/jobs/7366273"
                    ),
                    content=(
                        "<p>Machine learning for embodied robotics.</p>"
                        "<p>Duration: 12 weeks</p>"
                        "<h3>Qualifications</h3><p>Undergraduate students.</p>"
                    ),
                    departments=("Robotics",),
                ),
                RawOpportunityRecord(
                    id=999,
                    title="Finance Manager",
                    updated_at=datetime(2026, 7, 29, tzinfo=UTC),
                    location="Seattle, WA",
                    absolute_url=(
                        "https://job-boards.greenhouse.io/thealleninstitute/jobs/999"
                    ),
                    content="<p>Finance operations.</p>",
                    departments=("Finance",),
                ),
            ),
            invalid_count=0,
            retrieved_at=FIXED_TIME,
        )


@pytest.fixture
def opportunity_client(migrated_database_url: str) -> Iterator[TestClient]:
    application = create_app(
        Settings(
            app_environment="test",
            backend_cors_origins="http://localhost:3000",
            database_url=migrated_database_url,
            greenhouse_enabled_boards=("thealleninstitute,constructorknowledgelabs"),
            log_level="CRITICAL",
        )
    )
    application.state.opportunity_provider_override = OpportunityFixtureProvider()
    application.state.auth_verifier_override = StaticAccessTokenVerifier(
        {
            "opportunity-user-a-token": "supabase-opportunity-user-a",
            "opportunity-user-b-token": "supabase-opportunity-user-b",
        }
    )
    with TestClient(application) as client:
        client.headers.update({"Authorization": "Bearer opportunity-user-a-token"})
        yield client


def test_live_search_persists_evidence_and_reports_partial_source_failure(
    opportunity_client: TestClient,
) -> None:
    response = opportunity_client.post(
        "/api/v1/opportunities/search",
        json={"query": "machine learning robotics", "limit": 20},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["partialFailure"] is True
    assert body["rankingApplied"] is False
    assert len(body["results"]) == 1
    result = body["results"][0]
    assert result["sourceKind"] == "official-ats"
    assert result["evidenceConfidence"] == "high"
    assert result["workMode"] == "unclear"
    assert result["funding"] == "unclear"
    assert result["deadline"] is None
    assert result["duration"] == "12 weeks"
    assert result["countryCode"] == "US"
    assert result["isSaved"] is False
    assert result["applicationId"] is None
    assert body["sources"][1]["errorCode"] == "unreachable"


def test_save_track_update_and_reload_preserve_explicit_versioned_history(
    opportunity_client: TestClient,
) -> None:
    search = opportunity_client.post(
        "/api/v1/opportunities/search", json={"query": "robotics"}
    ).json()
    opportunity_id = search["results"][0]["id"]

    saved = opportunity_client.post(f"/api/v1/opportunities/{opportunity_id}/save")
    saved_again = opportunity_client.post(
        f"/api/v1/opportunities/{opportunity_id}/save"
    )
    assert saved.status_code == 201
    assert saved_again.status_code == 201
    assert saved.json()["opportunity"]["isSaved"] is True
    assert saved.json()["savedAt"].endswith("Z")
    saved_items = opportunity_client.get("/api/v1/opportunities/saved").json()["items"]
    assert len(saved_items) == 1

    created = opportunity_client.post(
        "/api/v1/applications", json={"opportunityId": opportunity_id}
    )
    duplicate = opportunity_client.post(
        "/api/v1/applications", json={"opportunityId": opportunity_id}
    )
    assert created.status_code == 201
    assert duplicate.json()["id"] == created.json()["id"]
    application = created.json()
    assert application["status"] == "saved"
    assert application["version"] == 1
    assert application["externalSubmissionPerformed"] is False
    assert application["createdAt"].endswith("Z")
    assert application["events"][0]["occurredAt"].endswith("Z")
    assert len(application["events"]) == 1

    updated = opportunity_client.put(
        f"/api/v1/applications/{application['id']}",
        json={
            "status": "applied",
            "notes": "Submitted through the official application page.",
            "followUpDate": date(2026, 8, 15).isoformat(),
            "expectedVersion": 1,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 2
    assert updated.json()["status"] == "applied"
    assert len(updated.json()["events"]) == 2

    conflict = opportunity_client.put(
        f"/api/v1/applications/{application['id']}",
        json={
            "status": "closed",
            "notes": "Stale editor",
            "followUpDate": None,
            "expectedVersion": 1,
        },
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "application_version_conflict"

    records = opportunity_client.get("/api/v1/applications").json()["items"]
    assert records[0]["version"] == 2
    assert records[0]["notes"].startswith("Submitted")


def test_tracker_requires_a_save_and_rejects_invalid_transition(
    opportunity_client: TestClient,
) -> None:
    opportunity_id = opportunity_client.post(
        "/api/v1/opportunities/search", json={"query": "robotics"}
    ).json()["results"][0]["id"]

    unsaved = opportunity_client.post(
        "/api/v1/applications", json={"opportunityId": opportunity_id}
    )
    assert unsaved.status_code == 409
    assert unsaved.json()["error"]["code"] == "opportunity_must_be_saved"

    opportunity_client.post(f"/api/v1/opportunities/{opportunity_id}/save")
    application = opportunity_client.post(
        "/api/v1/applications", json={"opportunityId": opportunity_id}
    ).json()
    invalid = opportunity_client.put(
        f"/api/v1/applications/{application['id']}",
        json={
            "status": "interviewing",
            "notes": "",
            "followUpDate": None,
            "expectedVersion": 1,
        },
    )

    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "invalid_application_transition"


def test_private_tracker_records_are_isolated_between_verified_subjects(
    opportunity_client: TestClient,
) -> None:
    search = opportunity_client.post(
        "/api/v1/opportunities/search", json={"query": "robotics"}
    ).json()
    opportunity_id = search["results"][0]["id"]
    assert (
        opportunity_client.post(
            f"/api/v1/opportunities/{opportunity_id}/save"
        ).status_code
        == 201
    )
    application = opportunity_client.post(
        "/api/v1/applications", json={"opportunityId": opportunity_id}
    ).json()

    opportunity_client.headers.update(
        {"Authorization": "Bearer opportunity-user-b-token"}
    )
    assert opportunity_client.get("/api/v1/opportunities/saved").json()["items"] == []
    foreign_update = opportunity_client.put(
        f"/api/v1/applications/{application['id']}",
        json={
            "status": "applied",
            "notes": "Attempted cross-account update.",
            "followUpDate": None,
            "expectedVersion": 1,
        },
    )
    assert foreign_update.status_code == 404
    assert foreign_update.json()["error"]["code"] == "application_not_found"
    assert (
        opportunity_client.delete(
            f"/api/v1/opportunities/{opportunity_id}/save"
        ).status_code
        == 204
    )

    opportunity_client.headers.update(
        {"Authorization": "Bearer opportunity-user-a-token"}
    )
    assert (
        len(opportunity_client.get("/api/v1/opportunities/saved").json()["items"]) == 1
    )
