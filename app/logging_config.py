"""Structured console logs with full secret redaction and no exception bodies."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any

SENSITIVE = re.compile(r"password|secret|token|authorization|cookie|api.?key|client.?id", re.I)


class RedactedJSON(logging.Formatter):
    def __init__(self, secrets: Iterable[str] = ()) -> None:
        super().__init__()
        self.secrets = tuple(sorted({s for s in secrets if s}, key=len, reverse=True))

    def clean(self, value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                str(k): "[REDACTED]" if SENSITIVE.search(str(k)) else self.clean(v)
                for k, v in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [self.clean(v) for v in value]
        if isinstance(value, str):
            for secret in self.secrets:
                value = value.replace(secret, "[REDACTED]")
            return re.sub(r"(?i)(bearer\s+)\S+", r"\1[REDACTED]", value)
        return (
            value
            if value is None or isinstance(value, (int, float, bool))
            else type(value).__name__
        )

    def format(self, record: logging.LogRecord) -> str:
        # Do not format traceback/exception text: upstream exceptions can contain headers.
        message = record.msg if isinstance(record.msg, dict) else record.getMessage()
        data = {
            "time": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": self.clean(message),
        }
        if record.exc_info and record.exc_info[0]:
            data["error_type"] = record.exc_info[0].__name__
        return json.dumps(data, ensure_ascii=True)


def configure_logging(environment: Mapping[str, str], *, level: str = "INFO") -> None:
    secrets = [v for k, v in environment.items() if SENSITIVE.search(k) and v]
    formatter = RedactedJSON(secrets)
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        root.addHandler(logging.StreamHandler())
    for handler in root.handlers:
        handler.setFormatter(formatter)
    # Access URLs and third-party debug bodies are not operational events.
    for name in ("httpx", "httpcore", "uvicorn.access"):
        logging.getLogger(name).setLevel(logging.WARNING)
