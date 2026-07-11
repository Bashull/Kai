from __future__ import annotations

import json
from typing import Any, Protocol
from urllib import request as urllib_request
from urllib.parse import urlparse

from .policy import AGENT_FIELDS


def build_http_payload(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if key in AGENT_FIELDS}


class StorageTransport(Protocol):
    def send(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class HttpStorageTransport:
    def __init__(self, base_url: str, token: str, timeout: float = 30.0) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Storage transport only allows local loopback HTTP endpoints")
        if not token:
            raise ValueError("Storage transport requires a non-empty token")
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def send(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(build_http_payload(payload), ensure_ascii=False).encode("utf-8")
        req = urllib_request.Request(
            f"{self.base_url}/v1/action",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
            method="POST",
        )
        with urllib_request.urlopen(req, timeout=self.timeout) as response:
            raw = response.read().decode("utf-8")
        decoded = json.loads(raw)
        if not isinstance(decoded, dict):
            raise ValueError("Storage agent returned a non-object JSON response")
        return decoded
