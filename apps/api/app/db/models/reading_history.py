from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class ReadingAnswer(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "reading_answers"
    __table_args__ = (
        UniqueConstraint("owner_id", "request_id"),
        Index(
            "ix_reading_answers_owner_document_created",
            "owner_id",
            "document_id",
            "created_at",
        ),
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("account_owners.id", ondelete="CASCADE")
    )
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_documents.id", ondelete="CASCADE")
    )
    request_id: Mapped[UUID]
    question: Mapped[str] = mapped_column(Text)
    result: Mapped[dict[str, object]] = mapped_column(JSON)
    model: Mapped[str] = mapped_column(String(80))
    disclosure_version: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
