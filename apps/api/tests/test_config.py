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


def test_greenhouse_origin_is_fixed_outside_owned_test_stubs() -> None:
    with pytest.raises(ValidationError, match="official HTTPS origin"):
        Settings(
            app_environment="production",
            greenhouse_base_url="https://example.org",
        )


def test_greenhouse_board_configuration_rejects_arbitrary_tokens() -> None:
    with pytest.raises(ValidationError, match="outside the allowlist"):
        Settings(greenhouse_enabled_boards="thealleninstitute,user-supplied-board")


def test_greenhouse_loopback_and_allowlist_subset_are_test_only_safe() -> None:
    settings = Settings(
        app_environment="e2e",
        greenhouse_base_url="http://127.0.0.1:8124/",
        greenhouse_enabled_boards="thealleninstitute,thealleninstitute",
    )

    assert settings.greenhouse_base_url == "http://127.0.0.1:8124"
    assert settings.greenhouse_board_keys == ["thealleninstitute"]
