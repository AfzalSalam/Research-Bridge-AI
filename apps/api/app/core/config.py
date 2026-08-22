from functools import lru_cache
from urllib.parse import urlparse
from uuid import UUID

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings for the API process."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Research Bridge API"
    app_version: str = "0.1.0"
    app_environment: str = "development"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    backend_cors_origins: str = "http://localhost:3000"
    database_url: str = (
        "postgresql+asyncpg://research_bridge:research_bridge_dev@"
        "localhost:5432/research_bridge"
    )
    database_echo: bool = False
    demo_owner_id: UUID = UUID("00000000-0000-4000-8000-000000000001")
    openalex_api_key: SecretStr | None = None
    openalex_base_url: str = "https://api.openalex.org"
    openalex_connect_timeout_seconds: float = Field(default=3.0, ge=0.1, le=30)
    openalex_read_timeout_seconds: float = Field(default=10.0, ge=0.1, le=60)
    openalex_write_timeout_seconds: float = Field(default=5.0, ge=0.1, le=30)
    openalex_pool_timeout_seconds: float = Field(default=2.0, ge=0.1, le=30)
    openalex_max_connections: int = Field(default=10, ge=1, le=50)
    openalex_max_keepalive_connections: int = Field(default=5, ge=0, le=25)
    openalex_max_attempts: int = Field(default=3, ge=1, le=4)
    openalex_backoff_base_seconds: float = Field(default=0.25, ge=0, le=5)
    openalex_backoff_cap_seconds: float = Field(default=2.0, ge=0, le=10)
    greenhouse_base_url: str = "https://boards-api.greenhouse.io"
    greenhouse_enabled_boards: str = (
        "thealleninstitute,constructorknowledgelabs,"
        "centerforstrategicandinternationalstudiesinc,verainstituteofjustice"
    )
    greenhouse_connect_timeout_seconds: float = Field(default=3.0, ge=0.1, le=30)
    greenhouse_read_timeout_seconds: float = Field(default=12.0, ge=0.1, le=60)
    greenhouse_write_timeout_seconds: float = Field(default=5.0, ge=0.1, le=30)
    greenhouse_pool_timeout_seconds: float = Field(default=2.0, ge=0.1, le=30)
    greenhouse_max_connections: int = Field(default=8, ge=1, le=20)
    greenhouse_max_keepalive_connections: int = Field(default=4, ge=0, le=10)
    greenhouse_max_attempts: int = Field(default=3, ge=1, le=4)
    greenhouse_backoff_base_seconds: float = Field(default=0.25, ge=0, le=5)
    greenhouse_backoff_cap_seconds: float = Field(default=2.0, ge=0, le=10)
    opportunity_stale_after_hours: int = Field(default=168, ge=1, le=720)
    openai_api_key: SecretStr | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_outreach_model: str = "gpt-5.6-terra"
    openai_connect_timeout_seconds: float = Field(default=3.0, ge=0.1, le=30)
    openai_read_timeout_seconds: float = Field(default=20.0, ge=0.1, le=120)
    openai_write_timeout_seconds: float = Field(default=5.0, ge=0.1, le=30)
    openai_pool_timeout_seconds: float = Field(default=2.0, ge=0.1, le=30)
    openai_max_connections: int = Field(default=5, ge=1, le=25)
    openai_max_keepalive_connections: int = Field(default=2, ge=0, le=10)
    openai_max_attempts: int = Field(default=2, ge=1, le=3)
    openai_backoff_base_seconds: float = Field(default=0.5, ge=0, le=5)
    openai_backoff_cap_seconds: float = Field(default=2.0, ge=0, le=10)
    discovery_cache_ttl_seconds: int = Field(default=600, ge=30, le=3600)
    discovery_cache_max_entries: int = Field(default=128, ge=1, le=1000)
    mentor_query_evidence_weight: float = Field(default=0.35, ge=0, le=1)
    mentor_profile_alignment_weight: float = Field(default=0.25, ge=0, le=1)
    mentor_supporting_depth_weight: float = Field(default=0.15, ge=0, le=1)
    mentor_recent_activity_weight: float = Field(default=0.15, ge=0, le=1)
    mentor_evidence_completeness_weight: float = Field(default=0.10, ge=0, le=1)

    @model_validator(mode="after")
    def validate_openalex_origin(self) -> "Settings":
        """Allow only the official provider, except for owned test loopback stubs."""

        parsed = urlparse(self.openalex_base_url)
        has_clean_origin = (
            parsed.username is None
            and parsed.password is None
            and parsed.params == ""
            and parsed.query == ""
            and parsed.fragment == ""
        )
        official_origin = (
            has_clean_origin
            and parsed.scheme == "https"
            and parsed.hostname == "api.openalex.org"
            and parsed.port is None
            and parsed.path.rstrip("/") == ""
        )
        loopback_test_origin = (
            has_clean_origin
            and self.app_environment in {"test", "e2e"}
            and parsed.scheme == "http"
            and parsed.hostname in {"127.0.0.1", "localhost"}
            and parsed.path.rstrip("/") == ""
        )
        if not (official_origin or loopback_test_origin):
            raise ValueError(
                "openalex_base_url must use the official HTTPS origin; "
                "loopback HTTP is allowed only in test or e2e"
            )
        self.openalex_base_url = self.openalex_base_url.rstrip("/")
        return self

    @model_validator(mode="after")
    def validate_greenhouse_configuration(self) -> "Settings":
        """Keep controlled extraction on one fixed origin and known boards."""

        from app.providers.opportunities import OPPORTUNITY_SOURCES

        parsed = urlparse(self.greenhouse_base_url)
        has_clean_origin = (
            parsed.username is None
            and parsed.password is None
            and parsed.params == ""
            and parsed.query == ""
            and parsed.fragment == ""
            and parsed.path.rstrip("/") == ""
        )
        official_origin = (
            has_clean_origin
            and parsed.scheme == "https"
            and parsed.hostname == "boards-api.greenhouse.io"
            and parsed.port is None
        )
        loopback_test_origin = (
            has_clean_origin
            and self.app_environment in {"test", "e2e"}
            and parsed.scheme == "http"
            and parsed.hostname in {"127.0.0.1", "localhost"}
        )
        if not (official_origin or loopback_test_origin):
            raise ValueError(
                "greenhouse_base_url must use the official HTTPS origin; "
                "loopback HTTP is allowed only in test or e2e"
            )
        board_keys = self.greenhouse_board_keys
        if not board_keys:
            raise ValueError("greenhouse_enabled_boards must enable at least one board")
        unknown = sorted(set(board_keys).difference(OPPORTUNITY_SOURCES))
        if unknown:
            raise ValueError(
                "greenhouse_enabled_boards contains a board outside the allowlist: "
                + ", ".join(unknown)
            )
        self.greenhouse_base_url = self.greenhouse_base_url.rstrip("/")
        return self

    @model_validator(mode="after")
    def validate_mentor_relevance_weights(self) -> "Settings":
        """Prevent configuration drift from silently changing total policy weight."""

        total = sum(
            (
                self.mentor_query_evidence_weight,
                self.mentor_profile_alignment_weight,
                self.mentor_supporting_depth_weight,
                self.mentor_recent_activity_weight,
                self.mentor_evidence_completeness_weight,
            )
        )
        if abs(total - 1) > 1e-9:
            raise ValueError("mentor relevance weights must total one")
        return self

    @model_validator(mode="after")
    def validate_openai_origin(self) -> "Settings":
        """Restrict model traffic to the official API or owned test loopback."""

        parsed = urlparse(self.openai_base_url)
        has_clean_origin = (
            parsed.username is None
            and parsed.password is None
            and parsed.params == ""
            and parsed.query == ""
            and parsed.fragment == ""
        )
        official_origin = (
            has_clean_origin
            and parsed.scheme == "https"
            and parsed.hostname == "api.openai.com"
            and parsed.port is None
            and parsed.path.rstrip("/") == "/v1"
        )
        loopback_test_origin = (
            has_clean_origin
            and self.app_environment in {"test", "e2e"}
            and parsed.scheme == "http"
            and parsed.hostname in {"127.0.0.1", "localhost"}
            and parsed.path.rstrip("/") in {"", "/v1"}
        )
        if not (official_origin or loopback_test_origin):
            raise ValueError(
                "openai_base_url must use the official HTTPS /v1 origin; "
                "loopback HTTP is allowed only in test or e2e"
            )
        self.openai_base_url = self.openai_base_url.rstrip("/")
        return self

    @property
    def cors_origins(self) -> list[str]:
        """Return normalized, non-empty configured browser origins."""

        return [
            origin.strip()
            for origin in self.backend_cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def greenhouse_board_keys(self) -> list[str]:
        """Return the ordered, de-duplicated configured allowlist subset."""

        values = [
            value.strip().casefold()
            for value in self.greenhouse_enabled_boards.split(",")
            if value.strip()
        ]
        return list(dict.fromkeys(values))


@lru_cache
def get_settings() -> Settings:
    """Load settings once for the process."""

    return Settings()
