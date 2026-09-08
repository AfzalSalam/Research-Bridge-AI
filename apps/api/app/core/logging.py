import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.core.request_context import get_request_id


class JsonFormatter(logging.Formatter):
    """Render privacy-safe application logs as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Inject context variables
        try:
            req_id = get_request_id()
            if req_id and req_id != "unavailable":
                payload["request_id"] = req_id
        except LookupError:
            pass

        for key in ("request_id", "method", "path", "status_code", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str) -> None:
    """Configure the application logger without mutating unrelated loggers."""

    logger = logging.getLogger("research_bridge")
    logger.setLevel(level.upper())
    logger.propagate = False
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
