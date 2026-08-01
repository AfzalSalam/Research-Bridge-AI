from functools import lru_cache
from uuid import UUID

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

    @property
    def cors_origins(self) -> list[str]:
        """Return normalized, non-empty configured browser origins."""

        return [
            origin.strip()
            for origin in self.backend_cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """Load settings once for the process."""

    return Settings()
