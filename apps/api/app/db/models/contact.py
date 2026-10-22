from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class PublicContactLookup(UUIDPrimaryKeyMixin, Base):
    """Public catalog evidence; contains no student profile or email draft."""

    __tablename__ = "public_contact_lookups"
    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("authors.id", ondelete="CASCADE"), index=True
    )
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict[str, object]] = mapped_column(JSON)
