import json
import logging
import os
from datetime import datetime, timezone
from logging.config import dictConfig


class EcsJsonFormatter(logging.Formatter):
    """Formats each record as one line of JSON using Elastic Common Schema field names."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "@timestamp": datetime.fromtimestamp(record.created, timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "log.level": record.levelname,
            "log.logger": record.name,
            "message": record.getMessage(),
            "process.thread.name": record.threadName,
        }
        if record.exc_info:
            error_type, error, _ = record.exc_info
            entry["error.type"] = error_type.__qualname__ if error_type else None
            entry["error.message"] = str(error)
            entry["error.stack_trace"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


def configure_logging():
    """
    With LOG_FORMAT=json the root logger and uvicorn's own loggers all write ECS JSON to stdout,
    replacing the handlers uvicorn installed before importing the app. Without it nothing changes,
    so a local run keeps uvicorn's usual output.
    """
    if os.getenv("LOG_FORMAT", "").lower() != "json":
        return
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"json": {"()": EcsJsonFormatter}},
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler", "formatter": "json", "stream": "ext://sys.stdout"},
        },
        "loggers": {
            "uvicorn": {"handlers": ["stdout"], "level": level, "propagate": False},
            "uvicorn.error": {"level": level},
            "uvicorn.access": {"handlers": ["stdout"], "level": level, "propagate": False},
        },
        "root": {"handlers": ["stdout"], "level": level},
    })
