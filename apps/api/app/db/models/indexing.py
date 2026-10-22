from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class IndexJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_index_jobs"
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_documents.id", ondelete="CASCADE"), unique=True
    )
    status: Mapped[str] = mapped_column(String(24), default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[UUID | None]
    last_error: Mapped[str | None] = mapped_column(String(100))
    disclosure_version: Mapped[str] = mapped_column(String(40))
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EmbeddingReservation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "embedding_reservations"
    __table_args__ = (
        Index("ix_embedding_reservations_owner_day", "owner_id", "day"),
        CheckConstraint("reserved_tokens > 0", name="positive_reservation"),
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("account_owners.id", ondelete="CASCADE")
    )
    # Deliberately no job FK: deleting a document cannot reset the daily budget.
    lease_token: Mapped[UUID] = mapped_column(unique=True)
    day: Mapped[date] = mapped_column(Date)
    reserved_tokens: Mapped[int] = mapped_column(Integer)
