from dataclasses import dataclass

import httpx2

from app.auth.contracts import AccessTokenVerifier
from app.auth.supabase import FixedAccessTokenVerifier, SupabaseTokenVerifier
from app.clients.greenhouse import GreenhouseClient
from app.clients.openalex import OpenAlexClient
from app.core.config import Settings
from app.providers.openai_outreach import OpenAIOutreachProvider
from app.services.search_cache import MemoryPaperSearchCache


@dataclass(frozen=True, slots=True)
class DiscoveryRuntime:
    """Application-scoped outbound resources shared across requests."""

    http_client: httpx2.AsyncClient
    provider: OpenAlexClient
    cache: MemoryPaperSearchCache


@dataclass(frozen=True, slots=True)
class OutreachRuntime:
    """Optional application-scoped model connection and provider."""

    http_client: httpx2.AsyncClient | None
    provider: OpenAIOutreachProvider | None


@dataclass(frozen=True, slots=True)
class OpportunityRuntime:
    """Application-scoped fixed-origin opportunity provider connection."""

    http_client: httpx2.AsyncClient
    provider: GreenhouseClient


@dataclass(frozen=True, slots=True)
class AuthRuntime:
    """Optional provider client and token verifier for private API routes."""

    http_client: httpx2.AsyncClient | None
    verifier: AccessTokenVerifier | None


def create_discovery_runtime(settings: Settings) -> DiscoveryRuntime:
    timeout = httpx2.Timeout(
        connect=settings.openalex_connect_timeout_seconds,
        read=settings.openalex_read_timeout_seconds,
        write=settings.openalex_write_timeout_seconds,
        pool=settings.openalex_pool_timeout_seconds,
    )
    limits = httpx2.Limits(
        max_connections=settings.openalex_max_connections,
        max_keepalive_connections=settings.openalex_max_keepalive_connections,
        keepalive_expiry=30,
    )
    http_client = httpx2.AsyncClient(
        base_url=settings.openalex_base_url,
        headers={"User-Agent": f"ResearchBridgeAI/{settings.app_version}"},
        timeout=timeout,
        limits=limits,
        follow_redirects=False,
        trust_env=False,
    )
    key = (
        settings.openalex_api_key.get_secret_value()
        if settings.openalex_api_key
        else None
    )
    provider = OpenAlexClient(
        http_client,
        api_key=key,
        max_attempts=settings.openalex_max_attempts,
        backoff_base_seconds=settings.openalex_backoff_base_seconds,
        backoff_cap_seconds=settings.openalex_backoff_cap_seconds,
    )
    cache = MemoryPaperSearchCache(
        ttl_seconds=settings.discovery_cache_ttl_seconds,
        max_entries=settings.discovery_cache_max_entries,
    )
    return DiscoveryRuntime(
        http_client=http_client,
        provider=provider,
        cache=cache,
    )


def create_outreach_runtime(settings: Settings) -> OutreachRuntime:
    if settings.openai_api_key is None:
        return OutreachRuntime(http_client=None, provider=None)
    timeout = httpx2.Timeout(
        connect=settings.openai_connect_timeout_seconds,
        read=settings.openai_read_timeout_seconds,
        write=settings.openai_write_timeout_seconds,
        pool=settings.openai_pool_timeout_seconds,
    )
    limits = httpx2.Limits(
        max_connections=settings.openai_max_connections,
        max_keepalive_connections=settings.openai_max_keepalive_connections,
        keepalive_expiry=30,
    )
    client = httpx2.AsyncClient(
        base_url=settings.openai_base_url,
        timeout=timeout,
        limits=limits,
        follow_redirects=False,
        trust_env=False,
    )
    provider = OpenAIOutreachProvider(
        client,
        api_key=settings.openai_api_key.get_secret_value(),
        model=settings.openai_outreach_model,
        max_attempts=settings.openai_max_attempts,
        backoff_base_seconds=settings.openai_backoff_base_seconds,
        backoff_cap_seconds=settings.openai_backoff_cap_seconds,
    )
    return OutreachRuntime(http_client=client, provider=provider)


def create_opportunity_runtime(settings: Settings) -> OpportunityRuntime:
    timeout = httpx2.Timeout(
        connect=settings.greenhouse_connect_timeout_seconds,
        read=settings.greenhouse_read_timeout_seconds,
        write=settings.greenhouse_write_timeout_seconds,
        pool=settings.greenhouse_pool_timeout_seconds,
    )
    limits = httpx2.Limits(
        max_connections=settings.greenhouse_max_connections,
        max_keepalive_connections=settings.greenhouse_max_keepalive_connections,
        keepalive_expiry=30,
    )
    client = httpx2.AsyncClient(
        base_url=settings.greenhouse_base_url,
        headers={"User-Agent": f"ResearchBridgeAI/{settings.app_version}"},
        timeout=timeout,
        limits=limits,
        follow_redirects=False,
        trust_env=False,
    )
    provider = GreenhouseClient(
        client,
        max_attempts=settings.greenhouse_max_attempts,
        backoff_base_seconds=settings.greenhouse_backoff_base_seconds,
        backoff_cap_seconds=settings.greenhouse_backoff_cap_seconds,
    )
    return OpportunityRuntime(http_client=client, provider=provider)


def create_auth_runtime(settings: Settings) -> AuthRuntime:
    """Create a production JWKS verifier or a strictly test/e2e-only verifier."""

    if settings.supabase_test_bearer_token is not None:
        return AuthRuntime(
            http_client=None,
            verifier=FixedAccessTokenVerifier(
                token=settings.supabase_test_bearer_token.get_secret_value(),
                subject=settings.supabase_test_subject or "",
            ),
        )
    if settings.supabase_url is None:
        return AuthRuntime(http_client=None, verifier=None)

    timeout = httpx2.Timeout(
        connect=settings.supabase_connect_timeout_seconds,
        read=settings.supabase_read_timeout_seconds,
        write=settings.supabase_read_timeout_seconds,
        pool=settings.supabase_connect_timeout_seconds,
    )
    client = httpx2.AsyncClient(
        base_url=settings.supabase_url,
        headers={"User-Agent": f"ResearchBridgeAI/{settings.app_version}"},
        timeout=timeout,
        follow_redirects=False,
        trust_env=False,
    )
    return AuthRuntime(
        http_client=client,
        verifier=SupabaseTokenVerifier(
            http_client=client,
            audience=settings.supabase_jwt_audience,
            issuer=f"{settings.supabase_url}/auth/v1",
            jwks_cache_ttl_seconds=settings.supabase_jwks_cache_ttl_seconds,
        ),
    )
