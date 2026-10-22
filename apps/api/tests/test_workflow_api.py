"""Exercise checkpointed HTTP workflow transitions and account isolation."""

import json
from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.auth_support import StaticAccessTokenVerifier, account_profile_payload
from tests.test_mentor_discovery import RepeatedAuthorProvider

QUERY = "human-centred clinical decision support"


@pytest.fixture
def workflow_client(migrated_database_url: str) -> Iterator[TestClient]:
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
        {"workflow-a": "supabase-workflow-a", "workflow-b": "supabase-workflow-b"}
    )
    with TestClient(application) as client:
        client.headers.update({"Authorization": "Bearer workflow-a"})
        assert (
            client.put(
                "/api/v1/profile", json=account_profile_payload("Asha")
            ).status_code
            == 200
        )
        yield client


def _start(client: TestClient) -> str:
    response = client.post(
        "/api/v1/workflow/start",
        json={"query": QUERY, "generationPreference": "deterministic"},
    )
    assert response.status_code == 200
    return str(response.json()["thread_id"])


def _stream_events(client: TestClient, thread_id: str) -> list[dict[str, object]]:
    response = client.get(f"/api/v1/workflow/{thread_id}/stream")
    assert response.status_code == 200
    assert "event: error" not in response.text
    assert "event: complete" in response.text
    return [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ") and line != "data: {}"
    ]


def test_workflow_keeps_state_across_requests_and_uses_account_evidence(
    workflow_client: TestClient,
) -> None:
    thread_id = _start(workflow_client)
    events = _stream_events(workflow_client, thread_id)
    discovery = events[0]["discover_mentors"]["discovery_response"]
    assert discovery["profileInputs"]["projectTitle"] == "Clinical decision support"
    candidate = discovery["candidates"][0]
    assert not any("generate_draft" in event for event in events)

    resumed = workflow_client.post(
        f"/api/v1/workflow/{thread_id}/resume",
        json={
            "selectedMentorId": candidate["id"],
            "selectedPaperIds": [candidate["supportingPapers"][0]["id"]],
        },
    )
    assert resumed.status_code == 200
    draft_events = _stream_events(workflow_client, thread_id)
    draft = draft_events[0]["generate_draft"]["draft_response"]
    assert draft["mentorId"] == candidate["id"]
    assert "Asha" in draft["body"]
    assert "Aarav Demo" not in draft["body"]
    assert draft["canSend"] is False
    assert draft["generation"]["mode"] == "deterministic"
    saved = workflow_client.get(f"/api/v1/outreach/drafts/{draft['id']}")
    assert saved.status_code == 200
    assert saved.json()["body"] == draft["body"]


def test_foreign_and_missing_workflows_cannot_be_streamed_or_resumed(
    workflow_client: TestClient,
) -> None:
    thread_id = _start(workflow_client)
    workflow_client.headers.update({"Authorization": "Bearer workflow-b"})
    selection = {
        "selectedMentorId": str(uuid4()),
        "selectedPaperIds": [str(uuid4())],
    }
    for target in (thread_id, str(uuid4())):
        denied_stream = workflow_client.get(f"/api/v1/workflow/{target}/stream")
        denied_resume = workflow_client.post(
            f"/api/v1/workflow/{target}/resume", json=selection
        )
        for response in (denied_stream, denied_resume):
            assert response.status_code == 404
            assert response.json()["error"]["code"] == "workflow_not_found"
            assert "text/event-stream" not in response.headers["content-type"]
            assert QUERY not in response.text

    # Denied calls neither executed discovery nor changed the pending selection.
    workflow_client.headers.update({"Authorization": "Bearer workflow-a"})
    events = _stream_events(workflow_client, thread_id)
    assert len(events) == 1
    assert "discover_mentors" in events[0]
    assert "generate_draft" not in events[0]


def test_workflow_requires_authentication_and_saved_profile(
    workflow_client: TestClient,
) -> None:
    workflow_client.headers.pop("Authorization")
    anonymous = workflow_client.post("/api/v1/workflow/start", json={"query": QUERY})
    assert anonymous.status_code == 401
    workflow_client.headers.update({"Authorization": "Bearer workflow-b"})
    missing = workflow_client.post("/api/v1/workflow/start", json={"query": QUERY})
    assert missing.status_code == 409
    assert missing.json()["error"]["code"] == "profile_required"


def test_workflow_does_not_silently_replace_unavailable_storage(
    workflow_client: TestClient,
) -> None:
    workflow_client.app.state.workflow_checkpointer = None
    response = workflow_client.post("/api/v1/workflow/start", json={"query": QUERY})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "workflow_unavailable"
