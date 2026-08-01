from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command


def build_alembic_config(database_url: str) -> Config:
    config_path = Path(__file__).parents[1] / "alembic.ini"
    config = Config(str(config_path))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


@pytest.fixture
def migrated_database_url(tmp_path: Path) -> Iterator[str]:
    database_path = tmp_path / "research-bridge-test.sqlite3"
    database_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    config = build_alembic_config(database_url)
    command.upgrade(config, "head")
    yield database_url
    command.downgrade(config, "base")
