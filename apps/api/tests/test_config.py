import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_openalex_origin_is_fixed_outside_owned_test_stubs() -> None:
    with pytest.raises(ValidationError, match="official HTTPS origin"):
        Settings(
            app_environment="production",
            openalex_base_url="https://example.org",
        )


@pytest.mark.parametrize(
    "value",
    [
        "https://user@api.openalex.org",
        "https://api.openalex.org?api_key=embedded",
        "https://api.openalex.org#fragment",
    ],
)
def test_openalex_origin_rejects_embedded_url_state(value: str) -> None:
    with pytest.raises(ValidationError, match="official HTTPS origin"):
        Settings(app_environment="production", openalex_base_url=value)


def test_loopback_provider_stub_is_allowed_only_for_tests() -> None:
    settings = Settings(
        app_environment="e2e",
        openalex_base_url="http://127.0.0.1:8123/",
    )

    assert settings.openalex_base_url == "http://127.0.0.1:8123"


def test_openai_origin_is_fixed_outside_owned_test_stubs() -> None:
    with pytest.raises(ValidationError, match="official HTTPS /v1 origin"):
        Settings(
            app_environment="production",
            openai_base_url="https://example.org/v1",
        )
