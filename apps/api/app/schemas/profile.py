"""Authenticated-account profile contracts, deliberately separate from demo data."""

import unicodedata
from typing import Annotated, Literal, Protocol

from pydantic import Field, StringConstraints, field_validator

from app.schemas.base import ApiModel

ProfileShortText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)
]


class StudentProfileFacts(Protocol):
    """The minimal verified facts consumed by relevance and outreach logic."""

    name: str
    program: str
    institution: str
    graduation_year: str
    research_interests: list[str]
    skills: list[str]
    project_title: str
    project_summary: str
    weekly_availability: Literal["5-10 hours", "10-15 hours", "15+ hours"]


class AccountProfile(ApiModel):
    """Verified student facts saved in one authenticated account's workspace."""

    name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=2, max_length=60)
    ]
    program: ProfileShortText
    institution: ProfileShortText
    graduation_year: Annotated[str, StringConstraints(pattern=r"^20\d{2}$")]
    research_interests: Annotated[
        list[ProfileShortText], Field(min_length=1, max_length=6)
    ]
    skills: Annotated[list[ProfileShortText], Field(min_length=1, max_length=8)]
    project_title: ProfileShortText
    project_summary: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=40, max_length=500)
    ]
    weekly_availability: Literal["5-10 hours", "10-15 hours", "15+ hours"]

    @field_validator("research_interests", "skills")
    @classmethod
    def require_unique_profile_terms(cls, values: list[str]) -> list[str]:
        normalized = [
            " ".join(unicodedata.normalize("NFKC", value).casefold().split())
            for value in values
        ]
        if len(normalized) != len(set(normalized)):
            raise ValueError("profile terms must not contain duplicates")
        return values


class AccountProfileReadResponse(ApiModel):
    """A profile is absent until the signed-in student explicitly saves it."""

    profile: AccountProfile | None
