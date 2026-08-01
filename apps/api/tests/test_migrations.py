import sqlite3
from pathlib import Path

import pytest

from alembic import command
from tests.conftest import build_alembic_config


def test_initial_migration_reaches_head_without_model_drift(tmp_path: Path) -> None:
    database_path = tmp_path / "migration-check.sqlite3"
    database_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    config = build_alembic_config(database_url)

    command.upgrade(config, "head")
    command.current(config, check_heads=True)
    command.check(config)

    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    expected_tables = {
        "account_owners",
        "application_events",
        "applications",
        "authors",
        "draft_papers",
        "institutions",
        "opportunities",
        "outreach_drafts",
        "paper_authors",
        "paper_topics",
        "papers",
        "profile_interests",
        "profile_preferences",
        "profile_projects",
        "profile_skills",
        "provenance_records",
        "saved_items",
        "student_profiles",
    }
    assert expected_tables <= table_names

    command.downgrade(config, "base")


def test_private_workflow_tables_reject_ambiguous_targets(tmp_path: Path) -> None:
    database_path = tmp_path / "constraint-check.sqlite3"
    database_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    config = build_alembic_config(database_url)
    command.upgrade(config, "head")

    with sqlite3.connect(database_path) as connection:
        owner_id = "00000000000040008000000000000001"
        connection.execute(
            "INSERT INTO account_owners (kind, auth_subject, id) VALUES (?, ?, ?)",
            ("demo", None, owner_id),
        )
        with pytest.raises(sqlite3.IntegrityError, match="exactly_one_target"):
            connection.execute(
                "INSERT INTO saved_items (owner_id, note, id) VALUES (?, ?, ?)",
                (owner_id, "", "00000000000040008000000000000002"),
            )
        with pytest.raises(sqlite3.IntegrityError, match="exactly_one_target"):
            connection.execute(
                "INSERT INTO applications "
                "(owner_id, target_label, source_url, status, notes, version, id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    owner_id,
                    "Ambiguous target",
                    "https://example.org/targets/ambiguous",
                    "saved",
                    "",
                    1,
                    "00000000000040008000000000000003",
                ),
            )

    command.downgrade(config, "base")
