from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app
from tests.auth_support import StaticAccessTokenVerifier


@pytest.fixture
def authenticated_client(migrated_database_url: str) -> Iterator[TestClient]:
    application = create_app(
        Settings(
            app_environment="test",
            backend_cors_origins="http://localhost:3000",
            database_url=migrated_database_url,
            log_level="CRITICAL",
        )
    )
    application.state.auth_verifier_override = StaticAccessTokenVerifier(
        {
            "user-a-token": "supabase-user-a",
            "user-b-token": "supabase-user-b",
        }
    )
    with TestClient(application) as client:
        yield client


def _profile_payload(name: str) -> dict[str, object]:
    return {
        "name": name,
        "program": "BTech Computer Science",
        "institution": "Research Bridge Institute",
        "graduationYear": "2027",
        "researchInterests": ["Information retrieval"],
        "skills": ["Python", "FastAPI"],
        "projectTitle": "Evidence-grounded discovery",
        "projectSummary": (
            "Built a provenance-aware academic discovery workflow with explicit "
            "uncertainty and carefully bounded source evidence."
        ),
        "weeklyAvailability": "10-15 hours",
    }


def test_private_profile_denies_anonymous_and_invalid_bearer_requests(
    authenticated_client: TestClient,
) -> None:
    anonymous = authenticated_client.get("/api/v1/profile")
    invalid = authenticated_client.get(
        "/api/v1/profile", headers={"Authorization": "Bearer forged-token"}
    )

    assert anonymous.status_code == 401
    assert anonymous.json()["error"]["code"] == "authentication_required"
    assert invalid.status_code == 401
    assert invalid.json()["error"]["code"] == "invalid_access_token"


def test_account_profile_is_created_and_read_only_in_its_verified_owner_scope(
    authenticated_client: TestClient,
) -> None:
    authenticated_client.headers.update({"Authorization": "Bearer user-a-token"})
    empty = authenticated_client.get("/api/v1/profile")
    created = authenticated_client.put("/api/v1/profile", json=_profile_payload("Asha"))

    authenticated_client.headers.update({"Authorization": "Bearer user-b-token"})
    other_user = authenticated_client.get("/api/v1/profile")

    authenticated_client.headers.update({"Authorization": "Bearer user-a-token"})
    reread = authenticated_client.get("/api/v1/profile")

    assert empty.json() == {"profile": None}
    assert created.status_code == 200
    assert other_user.json() == {"profile": None}
    assert reread.json()["profile"]["name"] == "Asha"


def test_demo_stays_public_and_cors_accepts_only_configured_bearer_requests(
    authenticated_client: TestClient,
) -> None:
    demo = authenticated_client.get("/api/v1/demo/bootstrap")
    preflight = authenticated_client.options(
        "/api/v1/profile",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert demo.status_code == 200
    assert preflight.status_code == 200
    assert "authorization" in preflight.headers["access-control-allow-headers"].lower()


def test_supabase_origin_and_test_bypass_configuration_fail_closed() -> None:
    with pytest.raises(ValidationError, match="official HTTPS project origin"):
        Settings(app_environment="production", supabase_url="https://example.org")
    with pytest.raises(ValidationError, match="allowed only in test or e2e"):
        Settings(
            app_environment="production",
            supabase_test_bearer_token="must-not-run-in-production",
            supabase_test_subject="subject",
        )
