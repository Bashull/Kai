from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SECRET_MARKERS = ("token", "authorization", "secret", "password", "api_key", "apikey")


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, child in value.items():
            lowered = key.lower()
            if any(marker in lowered for marker in SECRET_MARKERS):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redact(child)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


class AuditWriter:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def append(self, event: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = _redact(dict(event))
        record.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
