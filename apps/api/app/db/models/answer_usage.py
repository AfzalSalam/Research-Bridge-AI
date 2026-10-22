from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class AnswerReservation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "answer_reservations"
    __table_args__ = (
        UniqueConstraint("owner_id", "request_id"),
        Index("ix_answer_reservations_owner_day", "owner_id", "day"),
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("account_owners.id", ondelete="CASCADE")
    )
    request_id: Mapped[UUID]
    # No document FK: deleting a document must not restore consumed daily allowance.
    document_id: Mapped[UUID]
    day: Mapped[date] = mapped_column(Date)
    reserved_calls: Mapped[int] = mapped_column(Integer)
    disclosure_version: Mapped[str] = mapped_column(String(60))
    model: Mapped[str] = mapped_column(String(80))
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
