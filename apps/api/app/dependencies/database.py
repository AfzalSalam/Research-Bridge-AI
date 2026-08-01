from collections.abc import AsyncIterator
from typing import cast

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import Database


def get_database(request: Request) -> Database:
    """Return the configured process database resources."""

    return cast(Database, request.app.state.database)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Provide one transaction-scoped session per HTTP request."""

    database = get_database(request)
    async with database.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
