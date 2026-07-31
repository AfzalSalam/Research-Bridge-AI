from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def build_client() -> TestClient:
    settings = Settings(
        app_environment="test",
        backend_cors_origins="http://localhost:3000",
    )
    return TestClient(create_app(settings))


def test_health_returns_typed_process_status() -> None:
    with build_client() as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "research-bridge-api",
        "version": "0.1.0",
        "environment": "test",
    }


def test_health_allows_the_configured_frontend_origin() -> None:
    with build_client() as client:
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ("http://localhost:3000")
