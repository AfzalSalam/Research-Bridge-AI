from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.academic import Opportunity, ProvenanceRecord
from app.db.models.enums import ApplicationStatus, PublicEntityKind
from app.db.models.workflow import Application, ApplicationEvent, SavedItem
from app.providers.opportunities import NormalizedOpportunity


@dataclass(frozen=True, slots=True)
class StoredOpportunity:
    id: UUID
    value: NormalizedOpportunity


@dataclass(frozen=True, slots=True)
class SavedOpportunityRecord:
    saved_at: datetime
    opportunity: Opportunity


class OpportunityRepository(Protocol):
    async def persist(
        self, opportunities: tuple[NormalizedOpportunity, ...]
    ) -> tuple[StoredOpportunity, ...]: ...

    async def ownership_state(
        self, owner_id: UUID, opportunity_ids: Sequence[UUID]
    ) -> tuple[set[UUID], dict[UUID, UUID]]: ...

    async def get(self, opportunity_id: UUID) -> Opportunity | None: ...

    async def save(self, owner_id: UUID, opportunity_id: UUID) -> SavedItem: ...

    async def remove_save(self, owner_id: UUID, opportunity_id: UUID) -> None: ...

    async def list_saved(
        self, owner_id: UUID
    ) -> tuple[SavedOpportunityRecord, ...]: ...

    async def is_saved(self, owner_id: UUID, opportunity_id: UUID) -> bool: ...

    async def get_application_for_opportunity(
        self, owner_id: UUID, opportunity_id: UUID
    ) -> Application | None: ...

    async def create_application(
        self, owner_id: UUID, opportunity: Opportunity
    ) -> Application: ...

    async def list_applications(self, owner_id: UUID) -> tuple[Application, ...]: ...

    async def get_application_for_update(
        self, owner_id: UUID, application_id: UUID
    ) -> Application | None: ...

    async def append_application_event(
        self,
        application: Application,
        *,
        owner_id: UUID,
        from_status: ApplicationStatus,
        to_status: ApplicationStatus,
        note: str | None,
    ) -> ApplicationEvent: ...


class SqlAlchemyOpportunityRepository:
    """Persistence for source-linked opportunities and private workflow state."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def persist(
        self, opportunities: tuple[NormalizedOpportunity, ...]
    ) -> tuple[StoredOpportunity, ...]:
        stored: list[StoredOpportunity] = []
        for normalized in opportunities:
            opportunity = await self._session.scalar(
                select(Opportunity).where(
                    Opportunity.source_name == normalized.source_name,
                    Opportunity.source_record_id == normalized.source_record_id,
                )
            )
            if opportunity is None:
                opportunity = Opportunity(
                    source_name=normalized.source_name,
                    source_record_id=normalized.source_record_id,
                    source_kind=normalized.source_kind,
                    evidence_confidence=normalized.evidence_confidence,
                    opportunity_type=normalized.opportunity_type,
                    title=normalized.title,
                    organisation=normalized.organisation,
                    description=normalized.description,
                    research_fields=list(normalized.research_fields),
                    duration_text=normalized.duration_text,
                    eligibility_text=normalized.eligibility_text,
                    country_code=normalized.country_code,
                    location=normalized.location,
                    work_mode=normalized.work_mode,
                    funding=normalized.funding,
                    availability=normalized.availability,
                    deadline=normalized.deadline,
                    source_url=normalized.source_url,
                    application_url=normalized.application_url,
                    source_updated_at=normalized.source_updated_at,
                    last_verified_at=normalized.last_verified_at,
                    extraction_evidence=list(normalized.extraction_evidence),
                )
                self._session.add(opportunity)
                await self._session.flush()
            else:
                _apply_opportunity(opportunity, normalized)
            await self._upsert_provenance(opportunity, normalized)
            stored.append(StoredOpportunity(id=opportunity.id, value=normalized))
        await self._session.flush()
        return tuple(stored)

    async def ownership_state(
        self, owner_id: UUID, opportunity_ids: Sequence[UUID]
    ) -> tuple[set[UUID], dict[UUID, UUID]]:
        if not opportunity_ids:
            return set(), {}
        saved_values = (
            await self._session.scalars(
                select(SavedItem.opportunity_id).where(
                    SavedItem.owner_id == owner_id,
                    SavedItem.opportunity_id.in_(opportunity_ids),
                )
            )
        ).all()
        saved = {value for value in saved_values if value is not None}
        applications = (
            await self._session.execute(
                select(Application.opportunity_id, Application.id).where(
                    Application.owner_id == owner_id,
                    Application.opportunity_id.in_(opportunity_ids),
                )
            )
        ).all()
        return saved, {
            opportunity_id: application_id
            for opportunity_id, application_id in applications
            if opportunity_id is not None
        }

    async def get(self, opportunity_id: UUID) -> Opportunity | None:
        return await self._session.get(Opportunity, opportunity_id)

    async def save(self, owner_id: UUID, opportunity_id: UUID) -> SavedItem:
        existing = await self._session.scalar(
            select(SavedItem).where(
                SavedItem.owner_id == owner_id,
                SavedItem.opportunity_id == opportunity_id,
            )
        )
        if existing is not None:
            return existing
        saved = SavedItem(owner_id=owner_id, opportunity_id=opportunity_id, note="")
        self._session.add(saved)
        await self._session.flush()
        return saved

    async def remove_save(self, owner_id: UUID, opportunity_id: UUID) -> None:
        await self._session.execute(
            delete(SavedItem).where(
                SavedItem.owner_id == owner_id,
                SavedItem.opportunity_id == opportunity_id,
            )
        )

    async def list_saved(self, owner_id: UUID) -> tuple[SavedOpportunityRecord, ...]:
        rows = (
            await self._session.scalars(
                select(SavedItem)
                .where(
                    SavedItem.owner_id == owner_id,
                    SavedItem.opportunity_id.is_not(None),
                )
                .options(selectinload(SavedItem.opportunity))
                .order_by(SavedItem.saved_at.desc())
            )
        ).all()
        return tuple(
            SavedOpportunityRecord(saved_at=row.saved_at, opportunity=row.opportunity)
            for row in rows
            if row.opportunity is not None
        )

    async def is_saved(self, owner_id: UUID, opportunity_id: UUID) -> bool:
        value = await self._session.scalar(
            select(SavedItem.id).where(
                SavedItem.owner_id == owner_id,
                SavedItem.opportunity_id == opportunity_id,
            )
        )
        return value is not None

    async def get_application_for_opportunity(
        self, owner_id: UUID, opportunity_id: UUID
    ) -> Application | None:
        application: Application | None = await self._session.scalar(
            _application_statement().where(
                Application.owner_id == owner_id,
                Application.opportunity_id == opportunity_id,
            )
        )
        return application

    async def create_application(
        self, owner_id: UUID, opportunity: Opportunity
    ) -> Application:
        application = Application(
            owner_id=owner_id,
            opportunity_id=opportunity.id,
            target_label=opportunity.title,
            source_url=opportunity.source_url,
            status=ApplicationStatus.SAVED,
            notes="",
            follow_up_date=None,
            version=1,
        )
        application.events.append(
            ApplicationEvent(
                actor_owner_id=owner_id,
                sequence=1,
                from_status=None,
                to_status=ApplicationStatus.SAVED,
                note="Added to the tracker.",
            )
        )
        self._session.add(application)
        await self._session.flush()
        return application

    async def list_applications(self, owner_id: UUID) -> tuple[Application, ...]:
        applications = (
            await self._session.scalars(
                _application_statement()
                .where(Application.owner_id == owner_id)
                .order_by(Application.updated_at.desc(), Application.created_at.desc())
            )
        ).all()
        return tuple(applications)

    async def get_application_for_update(
        self, owner_id: UUID, application_id: UUID
    ) -> Application | None:
        application: Application | None = await self._session.scalar(
            _application_statement()
            .where(Application.owner_id == owner_id, Application.id == application_id)
            .with_for_update()
        )
        return application

    async def append_application_event(
        self,
        application: Application,
        *,
        owner_id: UUID,
        from_status: ApplicationStatus,
        to_status: ApplicationStatus,
        note: str | None,
    ) -> ApplicationEvent:
        event = ApplicationEvent(
            application=application,
            actor_owner_id=owner_id,
            sequence=len(application.events) + 1,
            from_status=from_status,
            to_status=to_status,
            note=note,
        )
        self._session.add(event)
        await self._session.flush()
        await self._session.refresh(application, attribute_names=["updated_at"])
        return event

    async def _upsert_provenance(
        self, opportunity: Opportunity, normalized: NormalizedOpportunity
    ) -> None:
        provenance = await self._session.scalar(
            select(ProvenanceRecord).where(
                ProvenanceRecord.entity_kind == PublicEntityKind.OPPORTUNITY,
                ProvenanceRecord.entity_id == opportunity.id,
                ProvenanceRecord.source_name == normalized.source_name,
                ProvenanceRecord.source_record_id == normalized.source_record_id,
            )
        )
        fields = [
            "title",
            "organisation",
            "description",
            "research_fields",
            "duration",
            "eligibility",
            "country_code",
            "location",
            "work_mode",
            "funding",
            "availability",
            "deadline",
            "application_url",
            "source_updated_at",
        ]
        if provenance is None:
            self._session.add(
                ProvenanceRecord(
                    entity_kind=PublicEntityKind.OPPORTUNITY,
                    entity_id=opportunity.id,
                    source_name=normalized.source_name,
                    source_record_id=normalized.source_record_id,
                    source_url=normalized.source_url,
                    retrieved_at=normalized.last_verified_at,
                    last_verified_at=normalized.last_verified_at,
                    content_hash=normalized.content_hash,
                    fields=fields,
                )
            )
            return
        provenance.source_url = normalized.source_url
        provenance.retrieved_at = normalized.last_verified_at
        provenance.last_verified_at = normalized.last_verified_at
        provenance.content_hash = normalized.content_hash
        provenance.fields = fields


def _apply_opportunity(
    opportunity: Opportunity, normalized: NormalizedOpportunity
) -> None:
    opportunity.source_kind = normalized.source_kind
    opportunity.evidence_confidence = normalized.evidence_confidence
    opportunity.opportunity_type = normalized.opportunity_type
    opportunity.title = normalized.title
    opportunity.organisation = normalized.organisation
    opportunity.description = normalized.description
    opportunity.research_fields = list(normalized.research_fields)
    opportunity.duration_text = normalized.duration_text
    opportunity.eligibility_text = normalized.eligibility_text
    opportunity.country_code = normalized.country_code
    opportunity.location = normalized.location
    opportunity.work_mode = normalized.work_mode
    opportunity.funding = normalized.funding
    opportunity.availability = normalized.availability
    opportunity.deadline = normalized.deadline
    opportunity.source_url = normalized.source_url
    opportunity.application_url = normalized.application_url
    opportunity.source_updated_at = normalized.source_updated_at
    opportunity.last_verified_at = normalized.last_verified_at
    opportunity.extraction_evidence = list(normalized.extraction_evidence)


def _application_statement() -> Select[tuple[Application]]:
    return select(Application).options(
        selectinload(Application.events), selectinload(Application.opportunity)
    )
