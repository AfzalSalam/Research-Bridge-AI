import asyncio
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routes.university import get_university_scanner
from app.clients.institutions import InstitutionRegistry
from app.dependencies.authentication import (
    AuthenticatedPrincipal,
    get_current_principal,
)
from app.dependencies.database import get_session
from app.dependencies.rate_limiting import rate_limit
from app.repositories.contact import ContactRepository
from app.schemas.contact import ContactLookupRequest, ContactLookupResponse
from app.services.contact import ContactService
from app.services.university_scan import UniversityScanService

router = APIRouter(prefix="/authors", tags=["discovery"])


def get_contact_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    scanner: Annotated[UniversityScanService, Depends(get_university_scanner)],
) -> ContactService:
    return ContactService(
        ContactRepository(session),
        scanner,
        cast(InstitutionRegistry, request.app.state.institution_registry),
    )


@router.post(
    "/{author_id}/public-email",
    response_model=ContactLookupResponse,
    dependencies=[rate_limit(10, 300)],
    summary="Find a selected researcher's evidenced public email",
)
async def lookup_public_email(
    author_id: UUID,
    body: ContactLookupRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    service: Annotated[ContactService, Depends(get_contact_service)],
) -> ContactLookupResponse:
    task = asyncio.create_task(service.lookup(author_id, principal.owner_id, body))
    try:
        while not task.done():
            await asyncio.wait({task}, timeout=0.25)
            if await request.is_disconnected():
                raise HTTPException(status_code=499, detail="Lookup cancelled.")
        return await task
    finally:
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)
