from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import ApiModel
from app.schemas.discovery import DiscoveredPaper


class ResearchSave(ApiModel):
    collection: str = Field(default="My research", min_length=1, max_length=120)
    note: str = Field(default="", max_length=5000)
    author_ids: list[UUID] = Field(default_factory=list, max_length=30)


class ResearchResult(ResearchSave):
    id: UUID
    paper: DiscoveredPaper
    updated_at: datetime


class RecipientUpdate(ApiModel):
    email: str = Field(
        min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    )
    expected_version: int = Field(ge=1)
    manually_confirmed: bool = False


class DraftSummary(ApiModel):
    id: UUID
    mentor_id: UUID | None
    recipient_display_name: str
    recipient_contact: str | None
    subject: str
    draft_version: int
    updated_at: datetime
