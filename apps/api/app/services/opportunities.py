from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from app.core.errors import AppError
from app.db.models.academic import Opportunity
from app.db.models.enums import AvailabilityStatus, FundingStatus, WorkMode
from app.providers.greenhouse.normalizer import (
    POLICY_VERSION,
    matches_query,
    normalize_board_record,
)
from app.providers.opportunities import (
    NormalizedOpportunity,
    OpportunityProvider,
    OpportunityProviderError,
    OpportunityProviderFailureKind,
    OpportunitySource,
)
from app.repositories.opportunities import OpportunityRepository, StoredOpportunity
from app.repositories.owners import OwnerRepository
from app.schemas.opportunities import (
    OpportunityExtractionEvidence,
    OpportunityResult,
    OpportunitySearchRequest,
    OpportunitySearchResponse,
    OpportunitySourceStatus,
    SavedOpportunity,
    SavedOpportunityListResponse,
)


class OpportunityReader(Protocol):
    async def search(
        self, request: OpportunitySearchRequest
    ) -> OpportunitySearchResponse: ...

    async def save(self, opportunity_id: UUID) -> SavedOpportunity: ...

    async def remove_save(self, opportunity_id: UUID) -> None: ...

    async def list_saved(self) -> SavedOpportunityListResponse: ...


class OpportunityService:
    """Retrieve, normalize, persist, and owner-scope verified opportunities."""

    def __init__(
        self,
        *,
        owner_id: UUID,
        owners: OwnerRepository,
        repository: OpportunityRepository,
        provider: OpportunityProvider,
        sources: Sequence[OpportunitySource],
        stale_after_hours: int,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._owner_id = owner_id
        self._owners = owners
        self._repository = repository
        self._provider = provider
        self._sources = tuple(sources)
        self._stale_after = timedelta(hours=stale_after_hours)
        self._clock = clock or (lambda: datetime.now(UTC))

    async def search(
        self, request: OpportunitySearchRequest
    ) -> OpportunitySearchResponse:
        outcomes = await asyncio.gather(
            *(self._provider.fetch_board(source) for source in self._sources),
            return_exceptions=True,
        )
        source_statuses: list[OpportunitySourceStatus] = []
        normalized: list[NormalizedOpportunity] = []
        retrieved_times: list[datetime] = []
        for source, outcome in zip(self._sources, outcomes, strict=True):
            if isinstance(outcome, OpportunityProviderError):
                source_statuses.append(_source_error(source, outcome))
                continue
            if isinstance(outcome, BaseException):
                raise outcome
            accepted = tuple(
                item
                for record in outcome.records
                if (
                    item := normalize_board_record(
                        record,
                        source_key=source.key,
                        organisation=source.organisation,
                        retrieved_at=outcome.retrieved_at,
                    )
                )
                is not None
            )
            normalized.extend(accepted)
            retrieved_times.append(outcome.retrieved_at)
            source_statuses.append(
                OpportunitySourceStatus(
                    key=source.key,
                    organisation=source.organisation,
                    status="success",
                    accepted_count=len(accepted),
                    invalid_count=outcome.invalid_count,
                )
            )

        stored = await self._repository.persist(tuple(normalized))
        visible = [
            item for item in stored if self._matches_filters(item.value, request)
        ]
        visible.sort(
            key=lambda item: (
                -_aware(item.value.source_updated_at).timestamp(),
                item.value.organisation.casefold(),
                item.value.title.casefold(),
            )
        )
        visible = visible[: request.limit]
        saved_ids, application_ids = await self._repository.ownership_state(
            self._owner_id, [item.id for item in visible]
        )
        now = self._clock()
        return OpportunitySearchResponse(
            query=" ".join(request.query.split()),
            results=[
                _from_normalized(
                    item,
                    is_saved=item.id in saved_ids,
                    application_id=application_ids.get(item.id),
                    now=now,
                    stale_after=self._stale_after,
                )
                for item in visible
            ],
            sources=source_statuses,
            partial_failure=any(item.status == "error" for item in source_statuses),
            policy_version=POLICY_VERSION,
            retrieved_at=max(retrieved_times, default=now),
        )

    async def save(self, opportunity_id: UUID) -> SavedOpportunity:
        opportunity = await self._required_opportunity(opportunity_id)
        await self._owners.get_or_create_demo(self._owner_id)
        saved = await self._repository.save(self._owner_id, opportunity_id)
        application = await self._repository.get_application_for_opportunity(
            self._owner_id, opportunity_id
        )
        return SavedOpportunity(
            saved_at=_aware(saved.saved_at),
            opportunity=_from_model(
                opportunity,
                is_saved=True,
                application_id=application.id if application else None,
                now=self._clock(),
                stale_after=self._stale_after,
            ),
        )

    async def remove_save(self, opportunity_id: UUID) -> None:
        await self._required_opportunity(opportunity_id)
        await self._repository.remove_save(self._owner_id, opportunity_id)

    async def list_saved(self) -> SavedOpportunityListResponse:
        rows = await self._repository.list_saved(self._owner_id)
        _, application_ids = await self._repository.ownership_state(
            self._owner_id, [row.opportunity.id for row in rows]
        )
        now = self._clock()
        return SavedOpportunityListResponse(
            items=[
                SavedOpportunity(
                    saved_at=_aware(row.saved_at),
                    opportunity=_from_model(
                        row.opportunity,
                        is_saved=True,
                        application_id=application_ids.get(row.opportunity.id),
                        now=now,
                        stale_after=self._stale_after,
                    ),
                )
                for row in rows
            ]
        )

    async def _required_opportunity(self, opportunity_id: UUID) -> Opportunity:
        opportunity = await self._repository.get(opportunity_id)
        if opportunity is None:
            raise AppError(
                code="opportunity_not_found",
                message="The opportunity was not found in the verified catalog.",
                status_code=404,
            )
        return opportunity

    def _matches_filters(
        self, opportunity: NormalizedOpportunity, request: OpportunitySearchRequest
    ) -> bool:
        if not matches_query(opportunity, request.query):
            return False
        if (
            request.country_code is not None
            and opportunity.country_code != request.country_code
        ):
            return False
        work_mode = _work_mode_filter(request.work_mode)
        if work_mode is not None and opportunity.work_mode is not work_mode:
            return False
        funding = _funding_filter(request.funding)
        if funding is not None and opportunity.funding is not funding:
            return False
        is_expired = (
            opportunity.deadline is not None
            and opportunity.deadline < self._clock().date()
        )
        return request.include_expired or not is_expired


def _source_error(
    source: OpportunitySource, error: OpportunityProviderError
) -> OpportunitySourceStatus:
    return OpportunitySourceStatus(
        key=source.key,
        organisation=source.organisation,
        status="error",
        accepted_count=0,
        invalid_count=0,
        error_code={
            OpportunityProviderFailureKind.INVALID_RESPONSE: "invalid-response",
            OpportunityProviderFailureKind.NETWORK: "unreachable",
            OpportunityProviderFailureKind.RATE_LIMIT: "rate-limited",
            OpportunityProviderFailureKind.REJECTED_REQUEST: "request-rejected",
            OpportunityProviderFailureKind.TEMPORARY: "temporarily-unavailable",
        }[error.kind],
        retryable=error.retryable,
    )


def _from_normalized(
    stored: StoredOpportunity,
    *,
    is_saved: bool,
    application_id: UUID | None,
    now: datetime,
    stale_after: timedelta,
) -> OpportunityResult:
    value = stored.value
    return OpportunityResult(
        id=stored.id,
        source_name=value.source_name,
        source_kind="official-ats",
        source_record_id=value.source_record_id,
        evidence_confidence="high",
        opportunity_type=value.opportunity_type,
        title=value.title,
        organisation=value.organisation,
        description_excerpt=value.description,
        research_fields=list(value.research_fields),
        duration=value.duration_text,
        eligibility=value.eligibility_text,
        country_code=value.country_code,
        location=value.location,
        work_mode=_public_work_mode(value.work_mode),
        funding=_public_funding(value.funding),
        availability=_public_availability(value.availability),
        deadline=value.deadline,
        source_url=value.source_url,
        application_url=value.application_url,
        source_updated_at=_aware(value.source_updated_at),
        last_verified_at=_aware(value.last_verified_at),
        is_stale=now - _aware(value.last_verified_at) > stale_after,
        is_expired=value.deadline is not None and value.deadline < now.date(),
        extraction_evidence=[
            OpportunityExtractionEvidence.model_validate(item)
            for item in value.extraction_evidence
        ],
        inclusion_signal=value.inclusion_signal,
        is_saved=is_saved,
        application_id=application_id,
    )


def _from_model(
    opportunity: Opportunity,
    *,
    is_saved: bool,
    application_id: UUID | None,
    now: datetime,
    stale_after: timedelta,
) -> OpportunityResult:
    evidence = [
        OpportunityExtractionEvidence.model_validate(item)
        for item in opportunity.extraction_evidence
    ]
    inclusion_value = next(
        (item.value for item in evidence if item.field == "inclusion"),
        f"{POLICY_VERSION}:unknown",
    )
    inclusion_signal = inclusion_value.rsplit(":", 1)[-1]
    source_updated_at = opportunity.source_updated_at or opportunity.last_verified_at
    if opportunity.application_url is None:
        raise RuntimeError("A live saved opportunity is missing its application URL.")
    return OpportunityResult(
        id=opportunity.id,
        source_name=opportunity.source_name,
        source_kind="official-ats",
        source_record_id=opportunity.source_record_id,
        evidence_confidence="high",
        opportunity_type=opportunity.opportunity_type,
        title=opportunity.title,
        organisation=opportunity.organisation,
        description_excerpt=opportunity.description,
        research_fields=list(opportunity.research_fields),
        duration=opportunity.duration_text,
        eligibility=opportunity.eligibility_text,
        country_code=opportunity.country_code,
        location=opportunity.location,
        work_mode=_public_work_mode(opportunity.work_mode),
        funding=_public_funding(opportunity.funding),
        availability=_public_availability(opportunity.availability),
        deadline=opportunity.deadline,
        source_url=opportunity.source_url,
        application_url=opportunity.application_url,
        source_updated_at=_aware(source_updated_at),
        last_verified_at=_aware(opportunity.last_verified_at),
        is_stale=now - _aware(opportunity.last_verified_at) > stale_after,
        is_expired=(
            opportunity.deadline is not None and opportunity.deadline < now.date()
        ),
        extraction_evidence=evidence,
        inclusion_signal=inclusion_signal,
        is_saved=is_saved,
        application_id=application_id,
    )


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _work_mode_filter(value: str | None) -> WorkMode | None:
    if value is None:
        return None
    return WorkMode.UNKNOWN if value == "unclear" else WorkMode(value)


def _funding_filter(value: str | None) -> FundingStatus | None:
    if value is None:
        return None
    return FundingStatus.UNKNOWN if value == "unclear" else FundingStatus(value)


def _public_work_mode(value: WorkMode) -> str:
    return "unclear" if value is WorkMode.UNKNOWN else value.value


def _public_funding(value: FundingStatus) -> str:
    return "unclear" if value is FundingStatus.UNKNOWN else value.value


def _public_availability(value: AvailabilityStatus) -> str:
    return "unclear" if value is AvailabilityStatus.UNKNOWN else value.value
