from typing import cast

from fastapi import Request

from app.services.demo import DemoService


def get_demo_service(request: Request) -> DemoService:
    """Resolve the configured demo service without coupling routes to its class."""

    return cast(DemoService, request.app.state.demo_service)
