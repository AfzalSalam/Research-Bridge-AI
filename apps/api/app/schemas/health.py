from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Public contract returned by the process health endpoint."""

    status: Literal["ok"] = "ok"
    service: str
    version: str
    environment: str
