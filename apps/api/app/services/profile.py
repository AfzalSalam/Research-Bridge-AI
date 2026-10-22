from typing import Protocol
from uuid import UUID

from app.db.models.profile import StudentProfileRecord
from app.fixtures.demo import fresh_profile
from app.repositories.owners import OwnerRepository
from app.repositories.profiles import ProfileRepository
from app.schemas.demo import StudentProfile
from app.schemas.profile import StudentProfileFacts


class ProfileReader(Protocol):
    """Profile facts consumed by discovery, with ownership set by composition."""

    async def get_profile(self) -> StudentProfileFacts: ...


class ProfileService:
    """Coordinates ownership and profile persistence inside one transaction."""

    def __init__(
        self,
        *,
        owner_id: UUID,
        owners: OwnerRepository,
        profiles: ProfileRepository,
    ) -> None:
        self._owner_id = owner_id
        self._owners = owners
        self._profiles = profiles

    async def get_profile(self) -> StudentProfile:
        record = await self._profiles.get_by_owner(self._owner_id)
        return fresh_profile() if record is None else self._to_schema(record)

    async def save_profile(self, profile: StudentProfile) -> StudentProfile:
        await self._owners.get_or_create_demo(self._owner_id)
        record = await self._profiles.upsert(self._owner_id, profile)
        return self._to_schema(record)

    @staticmethod
    def _to_schema(record: StudentProfileRecord) -> StudentProfile:
        if not record.projects:
            raise RuntimeError("A stored profile must contain at least one project.")
        project = record.projects[0]
        return StudentProfile(
            id="demo-student",
            name=record.display_name,
            program=record.degree_program,
            institution=record.institution_name,
            graduation_year=str(record.graduation_year),
            research_interests=[item.name for item in record.interests],
            skills=[item.name for item in record.skills],
            project_title=project.title,
            project_summary=project.summary,
            weekly_availability=record.weekly_availability.value,
        )
