from uuid import UUID

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class DocumentVector(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "document_vectors"
    __table_args__ = (
        UniqueConstraint("page_id", "start", "model"),
        CheckConstraint("start >= 0 AND end_offset > start", name="valid_offsets"),
    )
    page_id: Mapped[UUID] = mapped_column(
        ForeignKey("document_pages.id", ondelete="CASCADE"), index=True
    )
    start: Mapped[int] = mapped_column(Integer)
    end_offset: Mapped[int] = mapped_column(Integer)
    text_sha256: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(80))
    embedding: Mapped[list[float]] = mapped_column(
        VECTOR(1536).with_variant(JSON(), "sqlite")
    )
