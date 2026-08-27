from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from audio_studio.models import Availability, CapabilitySnapshot, SongRequest
from audio_studio.providers.base import MusicProviderAdapter


class RoutingError(RuntimeError):
    pass


@dataclass(frozen=True)
class RouteDecision:
    provider_id: str
    snapshot: CapabilitySnapshot
    compiled: dict
    rejected: tuple[dict, ...]


class MusicDirector:
    """Evidence-first router for neutral song Blueprints."""

    def __init__(self, providers: Iterable[MusicProviderAdapter]):
        self.providers = tuple(providers)
        if not self.providers:
            raise ValueError("at least one provider is required")
    def plan(self, request: SongRequest) -> RouteDecision:
        candidates: list[tuple[MusicProviderAdapter, CapabilitySnapshot]] = []
        rejected: list[dict] = []
        for provider in self.providers:
            snapshot = provider.probe()
            reason = self._rejection_reason(request, snapshot)
            if reason:
                rejected.append({"provider_id": provider.provider_id, "reason": reason})
            else:
                candidates.append((provider, snapshot))

        if not candidates:
            summary = ", ".join(f"{x['provider_id']}={x['reason']}" for x in rejected)
            raise RoutingError(f"no verified provider route: {summary}")

        provider, snapshot = min(
            candidates,
            key=lambda item: self._score(request, item[1]),
        )
        return RouteDecision(
            provider_id=provider.provider_id,
            snapshot=snapshot,
            compiled=provider.compile(request),
            rejected=tuple(rejected),
        )
    @staticmethod
    def _rejection_reason(request: SongRequest, snapshot: CapabilitySnapshot) -> str | None:
        if snapshot.availability is not Availability.AVAILABLE:
            return snapshot.availability.value
        missing = request.required_capabilities - snapshot.capabilities
        if missing:
            return "MISSING_CAPABILITIES:" + ",".join(sorted(missing))
        if request.local_only and snapshot.runtime != "LOCAL":
            return "REMOTE_RUNTIME"
        return None

    @staticmethod
    def _score(request: SongRequest, snapshot: CapabilitySnapshot) -> tuple[int, str]:
        if not request.prefer_free:
            return (0, snapshot.provider_id)
        rank = {"FREE": 0, "LOCAL": 0, "METERED": 1, "PAID": 2, "UNKNOWN": 3}
        return (rank.get(snapshot.cost_class, 3), snapshot.provider_id)