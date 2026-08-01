from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OpenAlexModel(BaseModel):
    """Provider DTO that tolerates fields OpenAlex adds outside our contract."""

    model_config = ConfigDict(extra="ignore")


class OpenAlexListMeta(OpenAlexModel):
    count: int | None = Field(default=None, ge=0)


class OpenAlexListEnvelope(OpenAlexModel):
    meta: OpenAlexListMeta
    results: list[dict[str, Any]]


class OpenAlexSource(OpenAlexModel):
    display_name: str | None = None


class OpenAlexLocation(OpenAlexModel):
    source: OpenAlexSource | None = None


class OpenAlexInstitutionGeo(OpenAlexModel):
    city: str | None = None


class OpenAlexInstitution(OpenAlexModel):
    id: str | None = None
    display_name: str | None = None
    ror: str | None = None
    country_code: str | None = None
    geo: OpenAlexInstitutionGeo | None = None


class OpenAlexAuthor(OpenAlexModel):
    id: str | None = None
    display_name: str | None = None
    orcid: str | None = None


class OpenAlexAuthorship(OpenAlexModel):
    author: OpenAlexAuthor
    institutions: list[OpenAlexInstitution] = Field(default_factory=list)
    is_corresponding: bool | None = None


class OpenAlexTopic(OpenAlexModel):
    id: str | None = None
    display_name: str | None = None
    score: float | None = Field(default=None, ge=0, le=1)


class OpenAlexWork(OpenAlexModel):
    id: str
    doi: str | None = None
    title: str | None = None
    publication_year: int | None = Field(default=None, ge=1000, le=2100)
    publication_date: date | None = None
    type: str | None = None
    language: str | None = None
    is_retracted: bool = False
    primary_location: OpenAlexLocation | None = None
    authorships: list[OpenAlexAuthorship] = Field(default_factory=list)
    abstract_inverted_index: dict[str, list[int]] | None = None
    topics: list[OpenAlexTopic] = Field(default_factory=list)
