from enum import StrEnum

from sqlalchemy import Enum as SqlEnum


class OwnerKind(StrEnum):
    DEMO = "demo"
    AUTHENTICATED = "authenticated"


class WeeklyAvailability(StrEnum):
    FIVE_TO_TEN = "5-10 hours"
    TEN_TO_FIFTEEN = "10-15 hours"
    FIFTEEN_PLUS = "15+ hours"


class EvidenceStrength(StrEnum):
    TITLE_ONLY = "title-only"
    ABSTRACT = "abstract"
    FULL_TEXT = "full-text"


class PublicEntityKind(StrEnum):
    INSTITUTION = "institution"
    AUTHOR = "author"
    PAPER = "paper"
    OPPORTUNITY = "opportunity"


class WorkMode(StrEnum):
    ON_SITE = "on-site"
    HYBRID = "hybrid"
    REMOTE = "remote"
    UNKNOWN = "unknown"


class FundingStatus(StrEnum):
    FUNDED = "funded"
    UNFUNDED = "unfunded"
    UNKNOWN = "unknown"


class AvailabilityStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class DraftGenerationMode(StrEnum):
    DETERMINISTIC = "deterministic"
    LLM = "llm"


class ApplicationStatus(StrEnum):
    SAVED = "saved"
    DRAFTING = "drafting"
    READY_FOR_REVIEW = "ready-for-review"
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    CLOSED = "closed"


def enum_type[EnumType: StrEnum](enum_class: type[EnumType], *, name: str) -> SqlEnum:
    """Create a portable validated enum with a named database check constraint."""

    return SqlEnum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )
