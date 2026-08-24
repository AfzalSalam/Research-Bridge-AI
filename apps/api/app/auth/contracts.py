from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class VerifiedIdentity:
    """Provider-verified identity data that is safe to map to a local owner."""

    subject: str


class AccessTokenVerifier(Protocol):
    """Verify one presented bearer token without exposing its contents."""

    async def verify_access_token(self, token: str) -> VerifiedIdentity: ...
