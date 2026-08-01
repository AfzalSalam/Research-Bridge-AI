from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import REQUEST_ID_HEADER, request_context_middleware
from app.db.session import Database, create_database


@asynccontextmanager
async def application_lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Release pooled database connections during process shutdown."""

    yield
    database = cast(Database, application.state.database)
    await database.engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an application with explicit, testable process settings."""

    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)
    application = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        description=(
            "Evidence-first academic discovery API. Phase 5 persists the fictional "
            "student profile while discovery remains deterministic demo data."
        ),
        lifespan=application_lifespan,
        openapi_tags=[
            {"name": "system", "description": "Process health and diagnostics."},
            {
                "name": "demo",
                "description": "Fictional contracts for the recruiter demo.",
            },
        ],
    )
    application.state.settings = app_settings
    application.state.database = create_database(app_settings)
    application.state.demo_service_override = None
    register_exception_handlers(application)
    application.middleware("http")(request_context_middleware)

    if app_settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=app_settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "OPTIONS"],
            allow_headers=["Accept", "Content-Type", REQUEST_ID_HEADER],
            expose_headers=[REQUEST_ID_HEADER],
        )

    application.include_router(api_router, prefix=app_settings.api_v1_prefix)
    return application


app = create_app()
