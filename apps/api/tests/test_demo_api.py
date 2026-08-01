from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.mock_demo import MockDemoService

FIXED_TIME = datetime(2026, 8, 1, 9, 30, tzinfo=UTC)


def build_client(*, raise_server_exceptions: bool = True) -> TestClient:
    application = create_app(
        Settings(
            app_environment="test",
            backend_cors_origins="http://localhost:3000",
            log_level="CRITICAL",
        )
    )
    application.state.demo_service_override = MockDemoService(clock=lambda: FIXED_TIME)
    return TestClient(
        application,
        raise_server_exceptions=raise_server_exceptions,
    )


def test_bootstrap_returns_the_versioned_fictional_catalog() -> None:
    with build_client() as client:
        response = client.get(
            "/api/v1/demo/bootstrap",
            headers={"X-Request-ID": "contract-test-001"},
        )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "contract-test-001"
    payload = response.json()
    assert payload["schemaVersion"] == 1
    assert payload["mode"] == "fictional-demo"
    assert payload["profile"]["id"] == "demo-student"
    assert len(payload["mentors"]) == 3
    assert len(payload["opportunities"]) == 3
    assert all("fictional" in mentor["name"].lower() for mentor in payload["mentors"])
    assert all(
        paper["sourceUrl"].startswith("https://example.org/")
        for mentor in payload["mentors"]
        for paper in mentor["papers"]
    )


def test_discovery_exposes_complete_partial_and_empty_outcomes() -> None:
    expected = {
        "complete": ("complete", 3, None),
        "partial": ("partial", 2, "One fictional source"),
        "empty": ("empty", 0, None),
    }
    with build_client() as client:
        for scenario, (status, count, warning) in expected.items():
            response = client.post(
                "/api/v1/demo/discovery",
                json={
                    "query": "human-centred AI for clinics",
                    "scenario": scenario,
                },
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload["status"] == status
            assert len(payload["mentorIds"]) == count
            if warning:
                assert payload["sourceWarning"].startswith(warning)
            else:
                assert payload["sourceWarning"] is None


def test_simulated_source_failure_uses_the_structured_error_contract() -> None:
    with build_client() as client:
        response = client.post(
            "/api/v1/demo/discovery",
            headers={"X-Request-ID": "source-failure-42"},
            json={
                "query": "human-centred AI for clinics",
                "scenario": "error",
            },
        )

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "demo_source_unavailable",
            "message": (
                "The fictional OpenAlex adapter timed out. "
                "No cached result was substituted."
            ),
            "requestId": "source-failure-42",
            "details": [],
        }
    }


def test_outreach_draft_is_grounded_in_selected_profile_and_paper() -> None:
    with build_client() as client:
        bootstrap = client.get("/api/v1/demo/bootstrap").json()
        profile = {**bootstrap["profile"], "name": "Riya Demo"}
        response = client.post(
            "/api/v1/demo/outreach-drafts",
            json={
                "profile": profile,
                "mentorId": "mentor-mira-sen",
                "paperIds": ["paper-context-before-confidence"],
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["mode"] == "deterministic-demo"
    assert payload["templateVersion"] == "phase-04.v1"
    assert payload["generatedAt"] == "2026-08-01T09:30:00Z"
    assert "Riya Demo" in payload["body"]
    assert "Context Before Confidence" in payload["body"]
    assert "Availability unknown" not in payload["body"]
    assert payload["paperIds"] == ["paper-context-before-confidence"]
    assert payload["claimEvidence"][0]["evidenceIds"] == [
        "paper-context-before-confidence"
    ]


def test_title_only_paper_never_produces_an_invented_technical_claim() -> None:
    with build_client() as client:
        profile = client.get("/api/v1/demo/bootstrap").json()["profile"]
        response = client.post(
            "/api/v1/demo/outreach-drafts",
            json={
                "profile": profile,
                "mentorId": "mentor-mira-sen",
                "paperIds": ["paper-feedback-under-shift"],
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert "only title-level metadata is available" in payload["body"]
    assert any(
        "supports no technical claim" in warning
        for warning in payload["uncertaintyWarnings"]
    )


def test_invalid_evidence_and_request_bodies_return_safe_field_details() -> None:
    with build_client() as client:
        profile = client.get("/api/v1/demo/bootstrap").json()["profile"]
        wrong_paper = client.post(
            "/api/v1/demo/outreach-drafts",
            json={
                "profile": profile,
                "mentorId": "mentor-mira-sen",
                "paperIds": ["paper-data-gaps-care-pathways"],
            },
        )
        invalid_query = client.post(
            "/api/v1/demo/discovery",
            json={"query": "short", "scenario": "complete"},
        )
        duplicate_papers = client.post(
            "/api/v1/demo/outreach-drafts",
            json={
                "profile": profile,
                "mentorId": "mentor-mira-sen",
                "paperIds": [
                    "paper-context-before-confidence",
                    "paper-context-before-confidence",
                ],
            },
        )

    assert wrong_paper.status_code == 422
    assert wrong_paper.json()["error"]["code"] == "paper_evidence_not_found"
    assert wrong_paper.json()["error"]["details"][0]["field"] == "paperIds"
    assert invalid_query.status_code == 422
    assert invalid_query.json()["error"]["code"] == "validation_error"
    assert invalid_query.json()["error"]["details"][0]["field"] == "query"
    assert duplicate_papers.status_code == 422
    assert duplicate_papers.json()["error"]["details"][0]["field"] == "paperIds"


def test_unknown_route_and_invalid_request_id_are_normalized() -> None:
    with build_client() as client:
        response = client.get(
            "/api/v1/does-not-exist",
            headers={"X-Request-ID": "contains spaces"},
        )

    request_id = response.headers["x-request-id"]
    assert response.status_code == 404
    assert request_id != "contains spaces"
    assert response.json()["error"]["requestId"] == request_id


def test_unexpected_failure_is_logged_but_returns_only_a_safe_error() -> None:
    class FailingDemoService(MockDemoService):
        async def bootstrap(self) -> None:
            raise RuntimeError("private implementation detail")

    application = create_app(
        Settings(app_environment="test", backend_cors_origins="", log_level="CRITICAL")
    )
    application.state.demo_service_override = FailingDemoService()
    with TestClient(application, raise_server_exceptions=False) as client:
        response = client.get(
            "/api/v1/demo/bootstrap",
            headers={"X-Request-ID": "unexpected-test-3"},
        )

    assert response.status_code == 500
    assert response.headers["x-request-id"] == "unexpected-test-3"
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "The server could not complete the request.",
            "requestId": "unexpected-test-3",
            "details": [],
        }
    }
    assert "private implementation detail" not in response.text


def test_openapi_documents_product_routes_and_error_schema() -> None:
    with build_client() as client:
        schema = client.get("/openapi.json").json()

    assert "/api/v1/demo/bootstrap" in schema["paths"]
    assert "/api/v1/demo/discovery" in schema["paths"]
    assert "/api/v1/demo/outreach-drafts" in schema["paths"]
    assert "/api/v1/demo/profile" in schema["paths"]
    assert "ErrorResponse" in schema["components"]["schemas"]
