from uuid import UUID

from sqlalchemy import JSON, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ResearchItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "research_items"
    __table_args__ = (UniqueConstraint("owner_id", "paper_id"),)
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("account_owners.id", ondelete="CASCADE"), index=True
    )
    paper_id: Mapped[UUID] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), index=True
    )
    collection: Mapped[str] = mapped_column(String(120), default="My research")
    note: Mapped[str] = mapped_column(Text, default="")
    author_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
