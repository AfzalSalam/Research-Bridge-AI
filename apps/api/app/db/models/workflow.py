from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import (
    ApplicationStatus,
    DraftGenerationMode,
    enum_type,
)

if TYPE_CHECKING:
    from app.db.models.academic import Author, Opportunity, Paper
    from app.db.models.ownership import AccountOwner


class SavedItem(UUIDPrimaryKeyMixin, Base):
    """Owner save pointing to exactly one supported public entity."""

    __tablename__ = "saved_items"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN paper_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN author_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN opportunity_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="exactly_one_target",
        ),
        UniqueConstraint("owner_id", "paper_id"),
        UniqueConstraint("owner_id", "author_id"),
        UniqueConstraint("owner_id", "opportunity_id"),
    )

    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("account_owners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    paper_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), nullable=True, index=True
    )
    author_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("authors.id", ondelete="CASCADE"), nullable=True, index=True
    )
    opportunity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    note: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    owner: Mapped[AccountOwner] = relationship(back_populates="saved_items")
    paper: Mapped[Paper | None] = relationship(back_populates="saved_items")
    author: Mapped[Author | None] = relationship(back_populates="saved_items")
    opportunity: Mapped[Opportunity | None] = relationship(back_populates="saved_items")


class OutreachDraft(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Editable outreach artifact; no sending capability is represented."""

    __tablename__ = "outreach_drafts"
    __table_args__ = (
        CheckConstraint("draft_version >= 1", name="draft_version_positive"),
    )

    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("account_owners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_author_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("authors.id", ondelete="SET NULL"), nullable=True, index=True
    )
    recipient_display_name: Mapped[str] = mapped_column(String(240), nullable=False)
    recipient_contact: Mapped[str | None] = mapped_column(String(320), nullable=True)
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    selected_student_facts: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    claim_evidence: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    uncertainty_warnings: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    evidence_map_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="verified-generated"
    )
    generation_mode: Mapped[DraftGenerationMode] = mapped_column(
        enum_type(DraftGenerationMode, name="draft_generation_mode"), nullable=False
    )
    template_version: Mapped[str] = mapped_column(String(80), nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    fallback_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    draft_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    owner: Mapped[AccountOwner] = relationship(back_populates="drafts")
    recipient_author: Mapped[Author | None] = relationship(back_populates="drafts")
    paper_links: Mapped[list[DraftPaper]] = relationship(
        back_populates="draft",
        cascade="all, delete-orphan",
        order_by="DraftPaper.position",
    )
    revisions: Mapped[list[OutreachDraftRevision]] = relationship(
        back_populates="draft",
        cascade="all, delete-orphan",
        order_by="OutreachDraftRevision.version",
    )


class DraftPaper(Base):
    __tablename__ = "draft_papers"
    __table_args__ = (
        CheckConstraint("position >= 0", name="position_non_negative"),
        UniqueConstraint("draft_id", "position"),
    )

    draft_id: Mapped[UUID] = mapped_column(
        ForeignKey("outreach_drafts.id", ondelete="CASCADE"), primary_key=True
    )
    paper_id: Mapped[UUID] = mapped_column(
        ForeignKey("papers.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    draft: Mapped[OutreachDraft] = relationship(back_populates="paper_links")
    paper: Mapped[Paper] = relationship(back_populates="draft_links")


class OutreachDraftRevision(UUIDPrimaryKeyMixin, Base):
    """Immutable subject/body snapshot for one owner edit version."""

    __tablename__ = "outreach_draft_revisions"
    __table_args__ = (
        CheckConstraint("version >= 1", name="version_positive"),
        UniqueConstraint("draft_id", "version"),
    )

    draft_id: Mapped[UUID] = mapped_column(
        ForeignKey("outreach_drafts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    editor_owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("account_owners.id", ondelete="RESTRICT"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    claim_evidence: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    evidence_map_status: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    draft: Mapped[OutreachDraft] = relationship(back_populates="revisions")


class Application(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Owner application targeting exactly one mentor or opportunity."""

    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN author_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN opportunity_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="exactly_one_target",
        ),
        CheckConstraint("version >= 1", name="version_positive"),
    )

    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("account_owners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("authors.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    opportunity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("opportunities.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    draft_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("outreach_drafts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_label: Mapped[str] = mapped_column(String(240), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    status: Mapped[ApplicationStatus] = mapped_column(
        enum_type(ApplicationStatus, name="application_status"), nullable=False
    )
    notes: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    follow_up_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    owner: Mapped[AccountOwner] = relationship(back_populates="applications")
    author: Mapped[Author | None] = relationship(back_populates="applications")
    opportunity: Mapped[Opportunity | None] = relationship(
        back_populates="applications"
    )
    draft: Mapped[OutreachDraft | None] = relationship()
    events: Mapped[list[ApplicationEvent]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationEvent.sequence",
    )


class ApplicationEvent(UUIDPrimaryKeyMixin, Base):
    """Append-only status history row for an application."""

    __tablename__ = "application_events"
    __table_args__ = (
        CheckConstraint("sequence >= 1", name="sequence_positive"),
        UniqueConstraint("application_id", "sequence"),
    )

    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("account_owners.id", ondelete="RESTRICT"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    from_status: Mapped[ApplicationStatus | None] = mapped_column(
        enum_type(ApplicationStatus, name="application_event_from_status"),
        nullable=True,
    )
    to_status: Mapped[ApplicationStatus] = mapped_column(
        enum_type(ApplicationStatus, name="application_event_to_status"),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    application: Mapped[Application] = relationship(back_populates="events")
