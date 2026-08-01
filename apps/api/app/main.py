from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import REQUEST_ID_HEADER, request_context_middleware
from app.services.mock_demo import MockDemoService


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an application with explicit, testable process settings."""

    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)
    application = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        description=(
            "Evidence-first academic discovery API. Phase 4 product routes expose "
            "only a visibly fictional, deterministic demo implementation."
        ),
        openapi_tags=[
            {"name": "system", "description": "Process health and diagnostics."},
            {
                "name": "demo",
                "description": "Stateless fictional contracts for the recruiter demo.",
            },
        ],
    )
    application.state.settings = app_settings
    application.state.demo_service = MockDemoService()
    register_exception_handlers(application)
    application.middleware("http")(request_context_middleware)

    if app_settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=app_settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Accept", "Content-Type", REQUEST_ID_HEADER],
            expose_headers=[REQUEST_ID_HEADER],
        )

    application.include_router(api_router, prefix=app_settings.api_v1_prefix)
    return application


app = create_app()
