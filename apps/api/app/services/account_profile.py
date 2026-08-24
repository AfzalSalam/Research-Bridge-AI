"""Owner-scoped profile service for authenticated students."""

from uuid import UUID

from app.core.errors import AppError
from app.db.models.profile import StudentProfileRecord
from app.repositories.profiles import ProfileRepository
from app.schemas.profile import AccountProfile


class AccountProfileService:
    """Read and write one authenticated owner's structured profile aggregate."""

    def __init__(self, *, owner_id: UUID, profiles: ProfileRepository) -> None:
        self._owner_id = owner_id
        self._profiles = profiles

    async def get_optional_profile(self) -> AccountProfile | None:
        record = await self._profiles.get_by_owner(self._owner_id)
        return None if record is None else self._to_schema(record)

    async def get_profile(self) -> AccountProfile:
        """Return a saved profile before a private workflow may reuse its facts."""

        profile = await self.get_optional_profile()
        if profile is None:
            raise AppError(
                code="profile_required",
                message="Save your profile before using it as outreach evidence.",
                status_code=409,
            )
        return profile

    async def save_profile(self, profile: AccountProfile) -> AccountProfile:
        record = await self._profiles.upsert(self._owner_id, profile)
        return self._to_schema(record)

    @staticmethod
    def _to_schema(record: StudentProfileRecord) -> AccountProfile:
        if not record.projects:
            raise RuntimeError("A stored profile must contain at least one project.")
        project = record.projects[0]
        return AccountProfile(
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
