"""Observability: structured JSON logging and PII-safe identifiers.

Phase 3. All logs go to stdout as single-line JSON so a log aggregator
(Datadog, CloudWatch, etc.) can parse them without extra configuration.
Customer IDs are hashed before logging: request flow stays correlatable
without storing PII in log storage.
"""

import hashlib
import json
import logging
import sys


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in (
            "request_id",
            "customer_id",
            "method",
            "path",
            "status_code",
            "stage",
            "model",
            "intent",
            "latency_ms",
            "prompt_tokens",
            "completion_tokens",
            "status",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def hash_customer_id(customer_id: str) -> str:
    """One-way hash for logs: correlatable, not reversible."""
    return hashlib.sha256(customer_id.encode()).hexdigest()[:12]


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
    # Silence uvicorn's text access logs; our middleware logs JSON instead.
    logging.getLogger("uvicorn.access").disabled = True
