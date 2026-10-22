from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ResearchDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "research_documents"
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("account_owners.id", ondelete="CASCADE"), index=True
    )
    paper_id: Mapped[UUID] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    byte_size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="uploading")
    reason: Mapped[str | None] = mapped_column(String(100))
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)


class DocumentPage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "document_pages"
    __table_args__ = (UniqueConstraint("document_id", "number"),)
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_documents.id", ondelete="CASCADE"), index=True
    )
    number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    chunks: Mapped[list[dict[str, int | str]]] = mapped_column(JSON)


class DocumentJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_jobs"
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_documents.id", ondelete="CASCADE"), unique=True
    )
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[UUID | None]
    last_error: Mapped[str | None] = mapped_column(String(100))


class DocumentBlob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Cleanup ledger deliberately survives owner/document cascade deletion."""

    __tablename__ = "document_blobs"
    owner_id: Mapped[UUID]
    document_id: Mapped[UUID] = mapped_column(unique=True)
    bucket: Mapped[str] = mapped_column(String(63))
    status: Mapped[str] = mapped_column(String(24), default="retained")
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[UUID | None]
    last_error: Mapped[str | None] = mapped_column(String(100))
