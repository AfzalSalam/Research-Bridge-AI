"""HTTP transport for an authenticated direct-university scan."""

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from app.clients.institutions import InstitutionRegistry
from app.dependencies.authentication import (
    AuthenticatedPrincipal,
    get_current_principal,
)
from app.dependencies.discovery import get_paper_discovery_service
from app.schemas.university import UniversityScanRequest, UniversityScanSnapshot
from app.services.discovery import PaperDiscoveryReader
from app.services.institution_discovery import GlobalUniversityDiscovery
from app.services.university_scan import UniversityScanService
from app.services.university_sources import UniversitySource

router = APIRouter(prefix="/discovery/universities", tags=["discovery"])
logger = logging.getLogger(__name__)


def get_university_scanner(request: Request) -> UniversityScanService:
    return cast(UniversityScanService, request.app.state.university_scanner)


def get_global_discovery(
    request: Request,
    papers: Annotated[PaperDiscoveryReader, Depends(get_paper_discovery_service)],
) -> GlobalUniversityDiscovery:
    return GlobalUniversityDiscovery(
        papers, cast(InstitutionRegistry, request.app.state.institution_registry)
    )


class UniversityEventStream(StreamingResponse):
    media_type = "text/event-stream"


@router.post(
    "/scan",
    response_model=UniversityScanSnapshot,
    response_class=UniversityEventStream,
    summary="Stream a bounded direct-university scan",
    description=(
        "SSE data events each contain a UniversityScanSnapshot. "
        "No arbitrary URLs are accepted."
    ),
    responses={200: {"content": {"text/event-stream": {"schema": {"type": "string"}}}}},
)
async def scan_universities(
    body: UniversityScanRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    scanner: Annotated[UniversityScanService, Depends(get_university_scanner)],
    worldwide: Annotated[GlobalUniversityDiscovery, Depends(get_global_discovery)],
) -> StreamingResponse:
    owner = str(principal.owner_id)
    token = scanner.reserve(owner)

    async def events() -> AsyncIterator[str]:
        try:
            started = time.monotonic()
            extra: dict[str, UniversitySource] = {}
            warnings: list[str] = []
            if body.universities is None:
                resolving = UniversityScanSnapshot(
                    state="scanning",
                    query=body.query,
                    target=body.target,
                    current_university="Finding relevant universities worldwide",
                )
                yield f"data: {resolving.model_dump_json()}\n\n"
                try:
                    async with asyncio.timeout(30):
                        extra, warnings = await worldwide.sources(body)
                except TimeoutError:
                    warnings = [
                        "Worldwide source selection timed out; "
                        "reviewed starting sources remain available."
                    ]
            async for snapshot in scanner.scan(
                body,
                extra_sources=extra,
                initial_elapsed=time.monotonic() - started,
                warnings=warnings,
            ):
                yield f"data: {snapshot.model_dump_json()}\n\n"
        except Exception:
            logger.exception("University scan failed")
            snapshot = UniversityScanSnapshot(
                state="error",
                query=body.query,
                target=body.target,
                warnings=[
                    "The scan could not finish. Please retry; "
                    "previous results remain visible."
                ],
            )
            yield f"data: {snapshot.model_dump_json()}\n\n"
        finally:
            scanner.release(owner, token)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        background=BackgroundTask(scanner.release, owner, token),
    )
