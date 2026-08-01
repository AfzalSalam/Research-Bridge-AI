import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def profile_client(migrated_database_url: str) -> Iterator[TestClient]:
    application = create_app(
        Settings(
            app_environment="test",
            backend_cors_origins="http://localhost:3000",
            database_url=migrated_database_url,
            log_level="CRITICAL",
        )
    )
    with TestClient(application) as client:
        yield client


def test_default_profile_read_does_not_create_private_data(
    profile_client: TestClient,
    migrated_database_url: str,
) -> None:
    response = profile_client.get("/api/v1/demo/profile")

    assert response.status_code == 200
    assert response.json()["name"] == "Aarav Demo"
    database_path = migrated_database_url.removeprefix("sqlite+aiosqlite:///")
    with sqlite3.connect(database_path) as connection:
        owner_count = connection.execute(
            "SELECT COUNT(*) FROM account_owners"
        ).fetchone()
        profile_count = connection.execute(
            "SELECT COUNT(*) FROM student_profiles"
        ).fetchone()
    assert owner_count == (0,)
    assert profile_count == (0,)


def test_profile_update_is_durable_and_bootstrap_uses_the_saved_value(
    profile_client: TestClient,
) -> None:
    profile = profile_client.get("/api/v1/demo/profile").json()
    updated = {
        **profile,
        "name": "Riya Demo",
        "researchInterests": ["Responsible AI", "Clinical NLP"],
        "skills": ["Python", "FastAPI"],
        "projectTitle": "Evidence-first research matching",
        "projectSummary": (
            "Built a provenance-aware workflow that keeps every recommendation "
            "connected to reviewable academic evidence."
        ),
        "weeklyAvailability": "10-15 hours",
    }

    saved = profile_client.put("/api/v1/demo/profile", json=updated)
    profile_read = profile_client.get("/api/v1/demo/profile")
    bootstrap = profile_client.get("/api/v1/demo/bootstrap")

    assert saved.status_code == 200
    assert saved.json() == updated
    assert profile_read.json() == updated
    assert bootstrap.json()["profile"] == updated


def test_profile_update_replaces_ordered_children_without_duplicates(
    profile_client: TestClient,
    migrated_database_url: str,
) -> None:
    profile = profile_client.get("/api/v1/demo/profile").json()
    first = {**profile, "researchInterests": ["NLP", "Human-centred AI"]}
    second = {**profile, "researchInterests": ["Information retrieval"]}

    assert profile_client.put("/api/v1/demo/profile", json=first).status_code == 200
    assert profile_client.put("/api/v1/demo/profile", json=second).status_code == 200

    database_path = migrated_database_url.removeprefix("sqlite+aiosqlite:///")
    with sqlite3.connect(database_path) as connection:
        interests = connection.execute(
            "SELECT name, position FROM profile_interests ORDER BY position"
        ).fetchall()
        counts = connection.execute(
            "SELECT (SELECT COUNT(*) FROM account_owners), "
            "(SELECT COUNT(*) FROM student_profiles)"
        ).fetchone()
    assert interests == [("Information retrieval", 0)]
    assert counts == (1, 1)


def test_duplicate_profile_terms_return_a_structured_validation_error(
    profile_client: TestClient,
) -> None:
    profile = profile_client.get("/api/v1/demo/profile").json()
    profile["skills"] = ["Python", " python "]

    response = profile_client.put("/api/v1/demo/profile", json=profile)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"][0]["field"] == "skills"


def test_database_failure_returns_a_safe_error_without_connection_details(
    tmp_path: Path,
) -> None:
    unavailable_path = (tmp_path / "missing" / "profile.sqlite3").as_posix()
    application = create_app(
        Settings(
            app_environment="test",
            backend_cors_origins="",
            database_url=f"sqlite+aiosqlite:///{unavailable_path}",
            log_level="CRITICAL",
        )
    )

    with TestClient(application, raise_server_exceptions=False) as client:
        response = client.get(
            "/api/v1/demo/profile",
            headers={"X-Request-ID": "database-failure-test"},
        )

    assert response.status_code == 500
    assert response.json()["error"] == {
        "code": "internal_error",
        "message": "The server could not complete the request.",
        "requestId": "database-failure-test",
        "details": [],
    }
    assert unavailable_path not in response.text
    assert "SELECT" not in response.text
