from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import REQUEST_ID_HEADER, request_context_middleware
from app.core.security_headers import security_headers_middleware
from app.db.session import Database, create_database
from app.runtime import (
    AuthRuntime,
    DiscoveryRuntime,
    OpportunityRuntime,
    OutreachRuntime,
    create_auth_runtime,
    create_discovery_runtime,
    create_opportunity_runtime,
    create_outreach_runtime,
)


@asynccontextmanager
async def application_lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Release pooled database and provider connections during shutdown."""

    app_settings = cast(Settings, application.state.settings)
    psycopg_url = app_settings.database_url.replace("postgresql+asyncpg", "postgresql")

    # LangGraph Postgres checkpointer — optional; degrades
    # gracefully when DB is absent or SQLite is used.
    pool: AsyncConnectionPool[AsyncConnection[dict[str, Any]]] | None = None
    if app_settings.database_url.startswith("postgres"):
        try:
            _pool = cast(
                AsyncConnectionPool[AsyncConnection[dict[str, Any]]],
                AsyncConnectionPool(
                    conninfo=psycopg_url,
                    max_size=20,
                    kwargs={
                        "autocommit": True,
                        "prepare_threshold": 0,
                        "row_factory": dict_row,
                    },
                    open=False,
                ),
            )
            await _pool.open()
            checkpointer = AsyncPostgresSaver(_pool)
            await checkpointer.setup()
            application.state.workflow_checkpointer = checkpointer
            pool = _pool
        except Exception:
            import logging as _logging

            _logging.getLogger(__name__).warning(
                "LangGraph checkpointer unavailable — workflow endpoints disabled",
                exc_info=True,
            )
            application.state.workflow_checkpointer = None
    else:
        application.state.workflow_checkpointer = None

    # Redis connection (used for rate limiting via fastapi_limiter.depends.RateLimiter)
    redis_client = None
    try:
        redis_client = redis.from_url(
            app_settings.redis_url, encoding="utf-8", decode_responses=True
        )
        await redis_client.ping()
        application.state.redis = redis_client
    except Exception:
        import logging as _logging

        _logging.getLogger(__name__).warning(
            "Redis unavailable — rate limiting degraded",
            exc_info=True,
        )
        application.state.redis = None

    try:
        yield
    finally:
        runtime = cast(DiscoveryRuntime, application.state.discovery_runtime)
        outreach_runtime = cast(OutreachRuntime, application.state.outreach_runtime)
        opportunity_runtime = cast(
            OpportunityRuntime, application.state.opportunity_runtime
        )
        auth_runtime = cast(AuthRuntime, application.state.auth_runtime)
        database = cast(Database, application.state.database)
        await runtime.http_client.aclose()
        if outreach_runtime.http_client is not None:
            await outreach_runtime.http_client.aclose()
        await opportunity_runtime.http_client.aclose()
        if auth_runtime.http_client is not None:
            await auth_runtime.http_client.aclose()
        await database.engine.dispose()
        if pool is not None:
            await pool.close()
        if redis_client is not None:
            await redis_client.aclose()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an application with explicit, testable process settings."""

    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)
    application = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        description=(
            "Evidence-first academic discovery API. Phase 9 adds source-linked "
            "research opportunities, private authenticated workspaces, and explicit "
            "application tracking."
        ),
        lifespan=application_lifespan,
        openapi_tags=[
            {"name": "system", "description": "Process health and diagnostics."},
            {
                "name": "demo",
                "description": "Fictional contracts for the recruiter demo.",
            },
            {
                "name": "discovery",
                "description": "Real paper evidence from bounded academic providers.",
            },
            {
                "name": "outreach",
                "description": "Human-reviewed drafts grounded in selected evidence.",
            },
            {
                "name": "opportunities",
                "description": "Allowlisted employer-published research openings.",
            },
            {
                "name": "applications",
                "description": "Explicit owner-scoped tracker state; no submission.",
            },
        ],
    )
    application.state.settings = app_settings
    application.state.database = create_database(app_settings)
    application.state.discovery_runtime = create_discovery_runtime(app_settings)
    application.state.outreach_runtime = create_outreach_runtime(app_settings)
    application.state.opportunity_runtime = create_opportunity_runtime(app_settings)
    application.state.auth_runtime = create_auth_runtime(app_settings)
    application.state.demo_service_override = None
    application.state.paper_provider_override = None
    application.state.outreach_generator_override = None
    application.state.opportunity_provider_override = None
    application.state.auth_verifier_override = None
    register_exception_handlers(application)
    application.middleware("http")(security_headers_middleware)
    application.middleware("http")(request_context_middleware)

    if app_settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=app_settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=[
                "Accept",
                "Authorization",
                "Content-Type",
                REQUEST_ID_HEADER,
            ],
            expose_headers=[REQUEST_ID_HEADER],
        )

    application.include_router(api_router, prefix=app_settings.api_v1_prefix)
    return application


app = create_app()
