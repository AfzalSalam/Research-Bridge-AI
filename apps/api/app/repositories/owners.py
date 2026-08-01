from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.enums import OwnerKind
from app.db.models.ownership import AccountOwner


class OwnerRepository(Protocol):
    """Ownership-anchor persistence required by private aggregates."""

    async def get_or_create_demo(self, owner_id: UUID) -> AccountOwner: ...


class SqlAlchemyOwnerRepository:
    """SQLAlchemy implementation scoped to one request transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_demo(self, owner_id: UUID) -> AccountOwner:
        owner = await self._session.get(AccountOwner, owner_id)
        if owner is not None:
            if owner.kind is not OwnerKind.DEMO or owner.auth_subject is not None:
                raise RuntimeError("The configured demo owner is not a demo account.")
            return owner

        owner = AccountOwner(
            id=owner_id,
            kind=OwnerKind.DEMO,
            auth_subject=None,
        )
        self._session.add(owner)
        await self._session.flush()
        return owner
