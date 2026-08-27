from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

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


class ReadOnlyCapabilityProbe:
    """Probe configuration or a harmless status endpoint; never generates audio."""

    def __init__(
        self,
        target: ProbeTarget,
        *,
        status_reader: Callable[[str], int] | None = None,
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
            status = self.status_reader(self.target.status_url)
        except Exception as exc:
            evidence["endpoint_state"] = "ERROR"
            evidence["error_type"] = type(exc).__name__
            return self._snapshot(Availability.OFFLINE, evidence)

        evidence["endpoint_state"] = "RESPONDED"
        evidence["http_status"] = status
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
