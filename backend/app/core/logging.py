import json
import logging
from datetime import datetime, timezone
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("method", "path"):
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: str) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(level.upper())
    if not any(isinstance(handler.formatter, JsonFormatter) for handler in root_logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        root_logger.addHandler(handler)
