"""Account deletion service — removes the authenticated owner aggregate."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.enums import OwnerKind
from app.db.models.ownership import AccountOwner


class AccountDeletionService:
    """Delete one authenticated owner and cascade all private records.

    Public academic catalog records (papers, authors, institutions, provenance)
    are never deleted — they are shared across the system and have no personal
    data. Only the owner aggregate and its private workspace are removed.
    """

    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def delete_authenticated_owner(self, owner_id: UUID) -> None:
        """Delete one authenticated owner row.

        SQLAlchemy cascade rules on AccountOwner handle:
        - student_profiles (+ interests, skills, projects)
        - saved_items
        - outreach_drafts (+ draft_revisions)
        - applications (+ application_events)
        """

        owner = await self._session.get(AccountOwner, owner_id)
        if owner is None:
            # Already gone — idempotent success
            return
        if owner.kind is not OwnerKind.AUTHENTICATED:
            # Never allow deletion of the shared demo owner
            raise RuntimeError(
                "Attempted to delete a non-authenticated owner. "
                "This is a programming error."
            )
        await self._session.delete(owner)
        # Flush within the request transaction; commit happens in get_session
        await self._session.flush()
