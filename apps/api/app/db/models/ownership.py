from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import OwnerKind, enum_type

if TYPE_CHECKING:
    from app.db.models.profile import StudentProfileRecord
    from app.db.models.workflow import Application, OutreachDraft, SavedItem


class AccountOwner(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Ownership anchor; authentication is intentionally implemented later."""

    __tablename__ = "account_owners"
    __table_args__ = (
        CheckConstraint(
            "(kind = 'demo' AND auth_subject IS NULL) OR "
            "(kind = 'authenticated' AND auth_subject IS NOT NULL)",
            name="kind_matches_auth_subject",
        ),
    )

    kind: Mapped[OwnerKind] = mapped_column(
        enum_type(OwnerKind, name="owner_kind"), nullable=False
    )
    auth_subject: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )

    profile: Mapped[StudentProfileRecord | None] = relationship(
        back_populates="owner", cascade="all, delete-orphan", uselist=False
    )
    saved_items: Mapped[list[SavedItem]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    drafts: Mapped[list[OutreachDraft]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    applications: Mapped[list[Application]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
