"""FastAPI dependencies that turn a verified bearer token into an owner scope."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, cast
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.contracts import AccessTokenVerifier
from app.auth.supabase import (
    AccessTokenInvalidError,
    AuthenticationProviderUnavailableError,
)
from app.core.errors import AppError
from app.dependencies.database import get_session
from app.repositories.owners import SqlAlchemyOwnerRepository
from app.runtime import AuthRuntime

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    """Local authorization scope produced only from a verified provider subject."""

    owner_id: UUID
    subject: str


def _get_verifier(request: Request) -> AccessTokenVerifier | None:
    override = request.app.state.auth_verifier_override
    if override is not None:
        return cast(AccessTokenVerifier, override)
    runtime = cast(AuthRuntime, request.app.state.auth_runtime)
    return runtime.verifier


async def get_optional_principal(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ],
) -> AuthenticatedPrincipal | None:
    """Return an owner scope when a valid bearer token is present, otherwise none."""

    if credentials is None:
        return None
    verifier = _get_verifier(request)
    if verifier is None:
        raise AppError(
            code="authentication_not_configured",
            message="Authentication is not configured for this environment.",
            status_code=503,
        )
    try:
        identity = await verifier.verify_access_token(credentials.credentials)
    except AccessTokenInvalidError as error:
        raise AppError(
            code="invalid_access_token",
            message="Your sign-in session is invalid or has expired.",
            status_code=401,
        ) from error
    except AuthenticationProviderUnavailableError as error:
        raise AppError(
            code="authentication_provider_unavailable",
            message=(
                "Sign-in verification is temporarily unavailable. Please try again."
            ),
            status_code=503,
        ) from error

    owner = await SqlAlchemyOwnerRepository(session).get_or_create_authenticated(
        identity.subject
    )
    return AuthenticatedPrincipal(owner_id=owner.id, subject=identity.subject)


async def get_current_principal(
    principal: Annotated[
        AuthenticatedPrincipal | None, Depends(get_optional_principal)
    ],
) -> AuthenticatedPrincipal:
    """Fail closed for every private route."""

    if principal is None:
        raise AppError(
            code="authentication_required",
            message="Sign in to access your private workspace.",
            status_code=401,
        )
    return principal
