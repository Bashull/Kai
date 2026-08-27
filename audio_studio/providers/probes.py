from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
from urllib.request import Request, urlopen

from audio_studio.models import Availability, CapabilitySnapshot


@dataclass(frozen=True)
class ProbeTarget:
    provider_id: str
    capabilities: frozenset[str]
    runtime: str
    cost_class: str = "UNKNOWN"
    status_url: str | None = None
    credential_pointer: str | None = None
    metadata: dict = field(default_factory=dict)
    expected_json: dict = field(default_factory=dict)
    policy_blocker: str | None = None


class ReadOnlyCapabilityProbe:
    """Probe configuration or a harmless status endpoint; never generates audio."""

    def __init__(
        self,
        target: ProbeTarget,
        *,
        status_reader: Callable[[str], int | tuple[int, dict]] | None = None,
        credential_resolver: Callable[[str], bool] | None = None,
    ):
        self.target = target
        self.status_reader = status_reader
        self.credential_resolver = credential_resolver
    def run(self) -> CapabilitySnapshot:
        evidence = {
            "probe_mode": "READ_ONLY",
            "generation_attempted": False,
            "status_url_configured": bool(self.target.status_url),
            "credential_pointer": self.target.credential_pointer,
            **self.target.metadata,
        }
        if self.target.policy_blocker:
            evidence["policy_blocker"] = self.target.policy_blocker
            evidence["endpoint_state"] = "POLICY_BLOCKED"
            return self._snapshot(Availability.TOOL_BLOCKED, evidence)
        if self.target.credential_pointer:
            if self.credential_resolver is None:
                evidence["credential_state"] = "UNRESOLVED"
                return self._snapshot(Availability.UNKNOWN, evidence)
            try:
                credential_present = self.credential_resolver(
                    self.target.credential_pointer
                )
            except Exception as exc:
                evidence["credential_state"] = "RESOLUTION_ERROR"
                evidence["error_type"] = type(exc).__name__
                return self._snapshot(Availability.UNKNOWN, evidence)
            evidence["credential_state"] = (
                "PRESENT" if credential_present else "MISSING"
            )
            if not credential_present:
                return self._snapshot(Availability.TOOL_BLOCKED, evidence)

        if not self.target.status_url:
            evidence["endpoint_state"] = "NOT_CONFIGURED"
            return self._snapshot(Availability.UNKNOWN, evidence)
        if self.status_reader is None:
            evidence["endpoint_state"] = "NOT_PROBED"
            return self._snapshot(Availability.UNKNOWN, evidence)
        try:
            observation = self.status_reader(self.target.status_url)
            status, body = observation if isinstance(observation, tuple) else (observation, {})
        except Exception as exc:
            evidence["endpoint_state"] = "ERROR"
            evidence["error_type"] = type(exc).__name__
            return self._snapshot(Availability.OFFLINE, evidence)

        evidence["endpoint_state"] = "RESPONDED"
        evidence["http_status"] = status
        if self.target.expected_json and not _contains_expected(
            body, self.target.expected_json
        ):
            evidence["endpoint_state"] = "INVALID_RESPONSE"
            return self._snapshot(Availability.OFFLINE, evidence)
        if 200 <= status < 400:
            availability = Availability.AVAILABLE
        elif status in {401, 403}:
            availability = Availability.TOOL_BLOCKED
        elif status == 429:
            availability = Availability.BLOCKED_QUOTA
        else:
            availability = Availability.OFFLINE
        return self._snapshot(availability, evidence)

    def _snapshot(
        self, availability: Availability, evidence: dict
    ) -> CapabilitySnapshot:
        return CapabilitySnapshot(
            provider_id=self.target.provider_id,
            availability=availability,
            capabilities=self.target.capabilities,
            cost_class=self.target.cost_class,
            runtime=self.target.runtime,
            evidence=evidence,
        )


def read_json_status(
    url: str, timeout_seconds: float = 5.0, max_bytes: int = 524288
) -> tuple[int, dict]:
    """Perform one GET and return status plus bounded decoded JSON."""
    if not 1 <= max_bytes <= 1048576:
        raise ValueError("max_bytes must be between 1 and 1048576")
    request = Request(url, method="GET", headers={
        "Accept": "application/json", "User-Agent": "curl/8.7.1"
    })
    with urlopen(request, timeout=timeout_seconds) as response:
        payload = response.read(max_bytes + 1)
        if len(payload) > max_bytes:
            raise ValueError("status response exceeds max_bytes")
        import json
        body = json.loads(payload.decode("utf-8"))
        if not isinstance(body, dict):
            raise ValueError("status response must be a JSON object")
        return response.status, body


def _contains_expected(actual: dict, expected: dict) -> bool:
    for key, value in expected.items():
        if key not in actual:
            return False
        if isinstance(value, dict):
            if not isinstance(actual[key], dict):
                return False
            if not _contains_expected(actual[key], value):
                return False
        elif actual[key] != value:
            return False
    return True


def read_text_status(url: str, timeout_seconds: float = 5.0) -> tuple[int, dict]:
    """Perform one GET and wrap a bounded plain-text identity response."""
    request = Request(url, method="GET", headers={
        "Accept": "text/plain",
        "User-Agent": "curl/8.7.1",
    })
    with urlopen(request, timeout=timeout_seconds) as response:
        text = response.read(4096).decode("utf-8").strip()
        return response.status, {"text": text}
