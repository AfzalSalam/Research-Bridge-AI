import json
from datetime import UTC, datetime
from pathlib import Path

from app.db.models.enums import FundingStatus, WorkMode
from app.providers.greenhouse.models import GreenhouseJob
from app.providers.greenhouse.normalizer import (
    html_to_plain_text,
    matches_query,
    normalize_board_record,
)
from app.providers.opportunities import RawOpportunityRecord

FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "greenhouse" / "jobs-representative.json"
)
FIXED_TIME = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


def records() -> list[dict[str, object]]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return payload["jobs"]


def raw_record(index: int) -> RawOpportunityRecord:
    job = GreenhouseJob.model_validate(records()[index])
    return RawOpportunityRecord(
        id=job.id,
        title=job.title,
        updated_at=job.updated_at,
        location=job.location.name,
        absolute_url=str(job.absolute_url),
        content=job.content,
        departments=tuple(item.name for item in job.departments),
    )


def test_explicit_fields_are_extracted_without_rendering_html() -> None:
    normalized = normalize_board_record(
        raw_record(0),
        source_key="thealleninstitute",
        organisation="Allen Institute for AI (Ai2)",
        retrieved_at=FIXED_TIME,
    )

    assert normalized is not None
    assert normalized.opportunity_type == "internship"
    assert normalized.work_mode is WorkMode.HYBRID
    assert normalized.funding is FundingStatus.FUNDED
    assert normalized.duration_text == "12 weeks"
    assert normalized.deadline is not None
    assert normalized.deadline.isoformat() == "2026-09-30"
    assert normalized.country_code == "US"
    assert normalized.eligibility_text is not None
    assert "Undergraduate" in normalized.eligibility_text
    assert "<p>" not in normalized.description
    assert matches_query(normalized, "machine learning robotics")
    assert not matches_query(normalized, "quantum chemistry")


def test_unstated_funding_mode_and_deadline_remain_unknown() -> None:
    normalized = normalize_board_record(
        raw_record(1),
        source_key="constructorknowledgelabs",
        organisation="Constructor Knowledge Labs",
        retrieved_at=FIXED_TIME,
    )

    assert normalized is not None
    assert normalized.work_mode is WorkMode.UNKNOWN
    assert normalized.funding is FundingStatus.UNKNOWN
    assert normalized.deadline is None
    assert normalized.duration_text is None
    assert normalized.country_code == "DE"


def test_unrelated_job_title_is_not_admitted_even_if_content_mentions_systems() -> None:
    normalized = normalize_board_record(
        raw_record(2),
        source_key="thealleninstitute",
        organisation="Allen Institute for AI (Ai2)",
        retrieved_at=FIXED_TIME,
    )

    assert normalized is None


def test_html_converter_decodes_entities_and_bounds_output() -> None:
    result = html_to_plain_text(
        "<p>Evidence &amp; safety</p><script>unsafe()</script>" + "x" * 30_000
    )

    assert result.startswith("Evidence & safety")
    assert len(result) == 20_000
    assert "<p>" not in result
    assert "unsafe" not in result


def test_negated_remote_wording_does_not_become_positive_work_mode_evidence() -> None:
    record = RawOpportunityRecord(
        id=42,
        title="Research Internship, Safety",
        updated_at=FIXED_TIME,
        location="Berlin, Germany",
        absolute_url="https://job-boards.greenhouse.io/example/jobs/42",
        content="<p>This is not a remote position.</p>",
        departments=("Safety",),
    )

    normalized = normalize_board_record(
        record,
        source_key="constructorknowledgelabs",
        organisation="Constructor Knowledge Labs",
        retrieved_at=FIXED_TIME,
    )

    assert normalized is not None
    assert normalized.work_mode is WorkMode.UNKNOWN
