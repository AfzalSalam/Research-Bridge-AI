import unicodedata
from typing import Protocol, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.enums import WeeklyAvailability
from app.db.models.profile import (
    ProfileInterest,
    ProfilePreference,
    ProfileProject,
    ProfileSkill,
    StudentProfileRecord,
)
from app.schemas.demo import StudentProfile
from app.schemas.profile import AccountProfile


def normalize_profile_value(value: str) -> str:
    """Create a Unicode-safe comparison key while preserving display text."""

    normalized = unicodedata.normalize("NFKC", value)
    return " ".join(normalized.casefold().split())


class ProfileRepository(Protocol):
    """Durable profile aggregate boundary."""

    async def get_by_owner(self, owner_id: UUID) -> StudentProfileRecord | None: ...

    async def upsert(
        self, owner_id: UUID, profile: StudentProfile | AccountProfile
    ) -> StudentProfileRecord: ...


class SqlAlchemyProfileRepository:
    """SQLAlchemy profile aggregate implementation with eager child loading."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_owner(self, owner_id: UUID) -> StudentProfileRecord | None:
        statement = (
            select(StudentProfileRecord)
            .where(StudentProfileRecord.owner_id == owner_id)
            .options(
                selectinload(StudentProfileRecord.interests),
                selectinload(StudentProfileRecord.skills),
                selectinload(StudentProfileRecord.projects),
                selectinload(StudentProfileRecord.preferences),
            )
        )
        return cast(StudentProfileRecord | None, await self._session.scalar(statement))

    async def upsert(
        self, owner_id: UUID, profile: StudentProfile | AccountProfile
    ) -> StudentProfileRecord:
        record = await self.get_by_owner(owner_id)
        if record is None:
            record = StudentProfileRecord(
                owner_id=owner_id,
                display_name=profile.name,
                degree_program=profile.program,
                institution_name=profile.institution,
                graduation_year=int(profile.graduation_year),
                weekly_availability=WeeklyAvailability(profile.weekly_availability),
            )
            record.preferences = ProfilePreference()
            self._session.add(record)
        else:
            record.display_name = profile.name
            record.degree_program = profile.program
            record.institution_name = profile.institution
            record.graduation_year = int(profile.graduation_year)
            record.weekly_availability = WeeklyAvailability(profile.weekly_availability)
            if record.preferences is None:
                record.preferences = ProfilePreference()
            record.interests.clear()
            record.skills.clear()
            record.projects.clear()
            # Delete old ordered children before inserting replacements so their
            # per-profile position constraints never overlap during one flush.
            await self._session.flush()

        record.interests = [
            ProfileInterest(
                name=value,
                normalized_name=normalize_profile_value(value),
                position=position,
            )
            for position, value in enumerate(profile.research_interests)
        ]
        record.skills = [
            ProfileSkill(
                name=value,
                normalized_name=normalize_profile_value(value),
                position=position,
            )
            for position, value in enumerate(profile.skills)
        ]
        record.projects = [
            ProfileProject(
                title=profile.project_title,
                summary=profile.project_summary,
                position=0,
            )
        ]
        await self._session.flush()
        return record
