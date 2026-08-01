from typing import Protocol

from app.schemas.demo import (
    DemoBootstrapResponse,
    DiscoveryRequest,
    DiscoveryResponse,
    OutreachDraft,
    OutreachDraftRequest,
)


class DemoService(Protocol):
    """Business boundary implemented by mock and future live adapters."""

    async def bootstrap(self) -> DemoBootstrapResponse: ...

    async def discover(self, request: DiscoveryRequest) -> DiscoveryResponse: ...

    async def create_outreach_draft(
        self, request: OutreachDraftRequest
    ) -> OutreachDraft: ...
