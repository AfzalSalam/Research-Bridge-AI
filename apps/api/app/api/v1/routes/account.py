"""Account management routes — deletion only for now."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.authentication import (
    AuthenticatedPrincipal,
    get_current_principal,
)
from app.dependencies.database import get_session
from app.services.account_deletion import AccountDeletionService

router = APIRouter(prefix="/account", tags=["account"])


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently delete the signed-in account and all private data",
    description=(
        "Deletes the owner aggregate including profile, saved opportunities, "
        "outreach drafts, draft revisions, applications, and application events. "
        "Public academic records (papers, authors, institutions) are never deleted. "
        "This action is irreversible and requires an authenticated request."
    ),
)
async def delete_account(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    service = AccountDeletionService(session=session)
    await service.delete_authenticated_owner(principal.owner_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
