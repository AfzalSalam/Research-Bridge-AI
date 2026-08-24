from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.enums import OwnerKind
from app.db.models.ownership import AccountOwner


class OwnerRepository(Protocol):
    """Ownership-anchor persistence required by private aggregates."""

    async def get_or_create_demo(self, owner_id: UUID) -> AccountOwner: ...

    async def get_or_create_authenticated(self, subject: str) -> AccountOwner: ...


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

    async def get_or_create_authenticated(self, subject: str) -> AccountOwner:
        owner = await self._session.scalar(
            select(AccountOwner).where(AccountOwner.auth_subject == subject)
        )
        if owner is not None:
            if (
                owner.kind is not OwnerKind.AUTHENTICATED
                or owner.auth_subject != subject
            ):
                raise RuntimeError(
                    "The authentication subject maps to an invalid owner."
                )
            return owner

        owner = AccountOwner(kind=OwnerKind.AUTHENTICATED, auth_subject=subject)
        self._session.add(owner)
        await self._session.flush()
        return owner
