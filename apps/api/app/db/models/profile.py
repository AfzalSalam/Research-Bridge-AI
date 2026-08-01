from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import WeeklyAvailability, enum_type

if TYPE_CHECKING:
    from app.db.models.ownership import AccountOwner


class StudentProfileRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One structured student profile per ownership anchor."""

    __tablename__ = "student_profiles"
    __table_args__ = (
        CheckConstraint(
            "graduation_year BETWEEN 2000 AND 2100", name="graduation_year_range"
        ),
    )

    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("account_owners.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(60), nullable=False)
    degree_program: Mapped[str] = mapped_column(String(120), nullable=False)
    institution_name: Mapped[str] = mapped_column(String(120), nullable=False)
    graduation_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    weekly_availability: Mapped[WeeklyAvailability] = mapped_column(
        enum_type(WeeklyAvailability, name="weekly_availability"), nullable=False
    )

    owner: Mapped[AccountOwner] = relationship(back_populates="profile")
    interests: Mapped[list[ProfileInterest]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="ProfileInterest.position",
        lazy="selectin",
    )
    skills: Mapped[list[ProfileSkill]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="ProfileSkill.position",
        lazy="selectin",
    )
    projects: Mapped[list[ProfileProject]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="ProfileProject.position",
        lazy="selectin",
    )
    preferences: Mapped[ProfilePreference | None] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )


class ProfileInterest(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "profile_interests"
    __table_args__ = (
        CheckConstraint("position >= 0", name="position_non_negative"),
        UniqueConstraint("profile_id", "normalized_name"),
        UniqueConstraint("profile_id", "position"),
    )

    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(120), nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    profile: Mapped[StudentProfileRecord] = relationship(back_populates="interests")


class ProfileSkill(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "profile_skills"
    __table_args__ = (
        CheckConstraint("position >= 0", name="position_non_negative"),
        UniqueConstraint("profile_id", "normalized_name"),
        UniqueConstraint("profile_id", "position"),
    )

    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(120), nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    profile: Mapped[StudentProfileRecord] = relationship(back_populates="skills")


class ProfileProject(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "profile_projects"
    __table_args__ = (
        CheckConstraint("position >= 0", name="position_non_negative"),
        UniqueConstraint("profile_id", "position"),
    )

    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    profile: Mapped[StudentProfileRecord] = relationship(back_populates="projects")


class ProfilePreference(TimestampMixin, Base):
    __tablename__ = "profile_preferences"

    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"), primary_key=True
    )
    preferred_countries: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    preferred_locations: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    preferred_institution_types: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    opportunity_work_modes: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    opportunity_funding_required: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )

    profile: Mapped[StudentProfileRecord] = relationship(back_populates="preferences")
