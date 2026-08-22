from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import (
    AvailabilityStatus,
    EvidenceStrength,
    FundingStatus,
    PublicEntityKind,
    WorkMode,
    enum_type,
)

if TYPE_CHECKING:
    from app.db.models.workflow import (
        Application,
        DraftPaper,
        OutreachDraft,
        SavedItem,
    )


class Institution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Normalized institution identity with provider provenance fields."""

    __tablename__ = "institutions"
    __table_args__ = (
        CheckConstraint(
            "country_code IS NULL OR length(country_code) = 2",
            name="country_code_length",
        ),
    )

    display_name: Mapped[str] = mapped_column(String(240), nullable=False)
    normalized_name: Mapped[str] = mapped_column(
        String(240), nullable=False, index=True
    )
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ror_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    openalex_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True
    )
    homepage_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    last_verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    authors: Mapped[list[Author]] = relationship(back_populates="institution")
    authorship_links: Mapped[list[PaperAuthorInstitution]] = relationship(
        back_populates="institution"
    )


class Author(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Academic author identity; unknown title and institution remain nullable."""

    __tablename__ = "authors"

    display_name: Mapped[str] = mapped_column(String(240), nullable=False)
    normalized_name: Mapped[str] = mapped_column(
        String(240), nullable=False, index=True
    )
    academic_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    institution_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("institutions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    orcid: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True)
    openalex_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True
    )
    semantic_scholar_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True
    )
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    last_verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    institution: Mapped[Institution | None] = relationship(back_populates="authors")
    paper_links: Mapped[list[PaperAuthor]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )
    saved_items: Mapped[list[SavedItem]] = relationship(back_populates="author")
    drafts: Mapped[list[OutreachDraft]] = relationship(
        back_populates="recipient_author"
    )
    applications: Mapped[list[Application]] = relationship(back_populates="author")


class Paper(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Normalized publication with explicit evidence and external identifiers."""

    __tablename__ = "papers"
    __table_args__ = (
        CheckConstraint(
            "publication_year BETWEEN 1000 AND 2100", name="publication_year_range"
        ),
    )

    title: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_title: Mapped[str] = mapped_column(
        String(500), nullable=False, index=True
    )
    publication_year: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, index=True
    )
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    work_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    is_retracted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    venue: Mapped[str | None] = mapped_column(String(240), nullable=True)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    doi: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    openalex_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True
    )
    semantic_scholar_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True
    )
    arxiv_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    evidence_strength: Mapped[EvidenceStrength] = mapped_column(
        enum_type(EvidenceStrength, name="evidence_strength"), nullable=False
    )
    primary_source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    last_verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    author_links: Mapped[list[PaperAuthor]] = relationship(
        back_populates="paper",
        cascade="all, delete-orphan",
        order_by="PaperAuthor.position",
    )
    topics: Mapped[list[PaperTopic]] = relationship(
        back_populates="paper",
        cascade="all, delete-orphan",
        order_by="PaperTopic.position",
    )
    saved_items: Mapped[list[SavedItem]] = relationship(back_populates="paper")
    draft_links: Mapped[list[DraftPaper]] = relationship(back_populates="paper")


class PaperAuthor(Base):
    __tablename__ = "paper_authors"
    __table_args__ = (
        CheckConstraint("position >= 0", name="position_non_negative"),
        UniqueConstraint("paper_id", "position"),
    )

    paper_id: Mapped[UUID] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True
    )
    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("authors.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_corresponding: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    paper: Mapped[Paper] = relationship(back_populates="author_links")
    author: Mapped[Author] = relationship(back_populates="paper_links")
    institution_links: Mapped[list[PaperAuthorInstitution]] = relationship(
        back_populates="paper_author",
        cascade="all, delete-orphan",
        order_by="PaperAuthorInstitution.position",
    )


class PaperAuthorInstitution(Base):
    """One institution listed for an author on a specific paper."""

    __tablename__ = "paper_author_institutions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["paper_id", "author_id"],
            ["paper_authors.paper_id", "paper_authors.author_id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("position >= 0", name="position_non_negative"),
        UniqueConstraint("paper_id", "author_id", "position"),
    )

    paper_id: Mapped[UUID] = mapped_column(primary_key=True)
    author_id: Mapped[UUID] = mapped_column(primary_key=True)
    institution_id: Mapped[UUID] = mapped_column(
        ForeignKey("institutions.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    paper_author: Mapped[PaperAuthor] = relationship(back_populates="institution_links")
    institution: Mapped[Institution] = relationship(back_populates="authorship_links")


class PaperTopic(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "paper_topics"
    __table_args__ = (
        CheckConstraint("position >= 0", name="position_non_negative"),
        UniqueConstraint("paper_id", "normalized_topic"),
        UniqueConstraint("paper_id", "openalex_topic_id"),
        UniqueConstraint("paper_id", "position"),
        CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 1)",
            name="score_range",
        ),
    )

    paper_id: Mapped[UUID] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic: Mapped[str] = mapped_column(String(160), nullable=False)
    normalized_topic: Mapped[str] = mapped_column(String(160), nullable=False)
    openalex_topic_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    paper: Mapped[Paper] = relationship(back_populates="topics")


class Opportunity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Normalized source-linked research opportunity."""

    __tablename__ = "opportunities"
    __table_args__ = (
        CheckConstraint(
            "country_code IS NULL OR length(country_code) = 2",
            name="country_code_length",
        ),
        UniqueConstraint("source_name", "source_record_id"),
    )

    source_name: Mapped[str] = mapped_column(String(80), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence_confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    opportunity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    organisation: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    research_fields: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    duration_text: Mapped[str | None] = mapped_column(String(160), nullable=True)
    eligibility_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    location: Mapped[str | None] = mapped_column(String(240), nullable=True)
    work_mode: Mapped[WorkMode] = mapped_column(
        enum_type(WorkMode, name="work_mode"), nullable=False
    )
    funding: Mapped[FundingStatus] = mapped_column(
        enum_type(FundingStatus, name="funding_status"), nullable=False
    )
    availability: Mapped[AvailabilityStatus] = mapped_column(
        enum_type(AvailabilityStatus, name="availability_status"), nullable=False
    )
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    application_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    extraction_evidence: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, nullable=False, default=list
    )

    saved_items: Mapped[list[SavedItem]] = relationship(back_populates="opportunity")
    applications: Mapped[list[Application]] = relationship(back_populates="opportunity")


class ProvenanceRecord(UUIDPrimaryKeyMixin, Base):
    """Provider evidence shared by public academic entity kinds."""

    __tablename__ = "provenance_records"
    __table_args__ = (
        UniqueConstraint("entity_kind", "entity_id", "source_name", "source_record_id"),
    )

    entity_kind: Mapped[PublicEntityKind] = mapped_column(
        enum_type(PublicEntityKind, name="public_entity_kind"), nullable=False
    )
    entity_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(80), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fields: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
