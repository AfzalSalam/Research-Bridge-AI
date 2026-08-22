from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.core.errors import AppError
from app.db.models.enums import ApplicationStatus
from app.db.models.workflow import Application
from app.repositories.opportunities import OpportunityRepository
from app.repositories.owners import OwnerRepository
from app.schemas.opportunities import (
    ApplicationCreateRequest,
    ApplicationEventResponse,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationUpdateRequest,
)

_TRANSITIONS: dict[ApplicationStatus, tuple[ApplicationStatus, ...]] = {
    ApplicationStatus.SAVED: (
        ApplicationStatus.DRAFTING,
        ApplicationStatus.APPLIED,
        ApplicationStatus.CLOSED,
    ),
    ApplicationStatus.DRAFTING: (
        ApplicationStatus.SAVED,
        ApplicationStatus.READY_FOR_REVIEW,
        ApplicationStatus.APPLIED,
        ApplicationStatus.CLOSED,
    ),
    ApplicationStatus.READY_FOR_REVIEW: (
        ApplicationStatus.DRAFTING,
        ApplicationStatus.APPLIED,
        ApplicationStatus.CLOSED,
    ),
    ApplicationStatus.APPLIED: (
        ApplicationStatus.INTERVIEWING,
        ApplicationStatus.CLOSED,
    ),
    ApplicationStatus.INTERVIEWING: (
        ApplicationStatus.APPLIED,
        ApplicationStatus.CLOSED,
    ),
    ApplicationStatus.CLOSED: (ApplicationStatus.SAVED,),
}


class ApplicationTrackerReader(Protocol):
    async def create(
        self, request: ApplicationCreateRequest
    ) -> ApplicationResponse: ...

    async def list(self) -> ApplicationListResponse: ...

    async def update(
        self, application_id: UUID, request: ApplicationUpdateRequest
    ) -> ApplicationResponse: ...


class ApplicationTrackerService:
    """Own explicit, versioned application state without external submission."""

    def __init__(
        self,
        *,
        owner_id: UUID,
        owners: OwnerRepository,
        repository: OpportunityRepository,
    ) -> None:
        self._owner_id = owner_id
        self._owners = owners
        self._repository = repository

    async def create(self, request: ApplicationCreateRequest) -> ApplicationResponse:
        if not await self._repository.is_saved(self._owner_id, request.opportunity_id):
            raise AppError(
                code="opportunity_must_be_saved",
                message="Save the verified opportunity before tracking it.",
                status_code=409,
            )
        existing = await self._repository.get_application_for_opportunity(
            self._owner_id, request.opportunity_id
        )
        if existing is not None:
            return application_response(existing)
        opportunity = await self._repository.get(request.opportunity_id)
        if opportunity is None:
            raise AppError(
                code="opportunity_not_found",
                message="The opportunity was not found in the verified catalog.",
                status_code=404,
            )
        await self._owners.get_or_create_demo(self._owner_id)
        application = await self._repository.create_application(
            self._owner_id, opportunity
        )
        return application_response(application)

    async def list(self) -> ApplicationListResponse:
        applications = await self._repository.list_applications(self._owner_id)
        return ApplicationListResponse(
            items=[application_response(item) for item in applications]
        )

    async def update(
        self, application_id: UUID, request: ApplicationUpdateRequest
    ) -> ApplicationResponse:
        application = await self._repository.get_application_for_update(
            self._owner_id, application_id
        )
        if application is None:
            raise AppError(
                code="application_not_found",
                message="The application record was not found.",
                status_code=404,
            )
        if application.version != request.expected_version:
            raise AppError(
                code="application_version_conflict",
                message="This application changed after the editor was loaded.",
                status_code=409,
            )
        if (
            request.status is not application.status
            and request.status not in _TRANSITIONS[application.status]
        ):
            allowed = ", ".join(item.value for item in _TRANSITIONS[application.status])
            raise AppError(
                code="invalid_application_transition",
                message="That application status transition is not allowed.",
                status_code=409,
                details=[
                    {
                        "field": "status",
                        "message": f"Allowed next statuses: {allowed}.",
                        "type": "value_error.transition",
                    }
                ],
            )
        previous_status = application.status
        changed_status = request.status is not previous_status
        changed_details = (
            request.notes != application.notes
            or request.follow_up_date != application.follow_up_date
        )
        if not changed_status and not changed_details:
            return application_response(application)
        application.status = request.status
        application.notes = request.notes
        application.follow_up_date = request.follow_up_date
        application.version += 1
        await self._repository.append_application_event(
            application,
            owner_id=self._owner_id,
            from_status=previous_status,
            to_status=request.status,
            note=(
                "Status changed by the user."
                if changed_status
                else "Notes or follow-up date updated by the user."
            ),
        )
        return application_response(application)


def application_response(application: Application) -> ApplicationResponse:
    if application.opportunity_id is None:
        raise RuntimeError("Phase 9 tracker response requires an opportunity target.")
    return ApplicationResponse(
        id=application.id,
        opportunity_id=application.opportunity_id,
        target_label=application.target_label,
        source_url=application.source_url,
        status=application.status,
        notes=application.notes,
        follow_up_date=application.follow_up_date,
        version=application.version,
        created_at=_aware(application.created_at),
        updated_at=_aware(application.updated_at),
        events=[
            ApplicationEventResponse(
                sequence=event.sequence,
                from_status=event.from_status,
                to_status=event.to_status,
                note=event.note,
                occurred_at=_aware(event.occurred_at),
            )
            for event in application.events
        ],
        allowed_next_statuses=list(_TRANSITIONS[application.status]),
    )


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
