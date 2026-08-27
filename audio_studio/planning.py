from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from audio_studio.director import MusicDirector, RoutingError
from audio_studio.models import CapabilitySnapshot, SongRequest
from audio_studio.providers.base import MusicProviderAdapter


@dataclass(frozen=True)
class DryRunReport:
    case_id: str
    status: str
    selected_provider: str | None
    compiled: dict | None
    rejected: tuple[dict, ...]
    snapshots: tuple[dict, ...]
    generation_attempted: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def plan_dry_run(
    request: SongRequest,
    providers: Iterable[MusicProviderAdapter],
) -> DryRunReport:
    """Plan and compile only. This function cannot call generate()."""
    provider_set = tuple(providers)
    snapshots: list[CapabilitySnapshot] = []
    frozen_providers: list[MusicProviderAdapter] = []
    for provider in provider_set:
        snapshot = provider.probe()
        snapshots.append(snapshot)
        frozen_providers.append(_FrozenProbeAdapter(provider, snapshot))

    try:
        decision = MusicDirector(frozen_providers).plan(request)
    except RoutingError:
        rejected = tuple(
            {
                "provider_id": snapshot.provider_id,
                "reason": MusicDirector._rejection_reason(request, snapshot),
            }
            for snapshot in snapshots
        )
        return DryRunReport(
            case_id=request.case_id,
            status="BLOCKED",
            selected_provider=None,
            compiled=None,
            rejected=rejected,
            snapshots=tuple(_snapshot_dict(item) for item in snapshots),
        )

    return DryRunReport(
        case_id=request.case_id,
        status="PLANNED",
        selected_provider=decision.provider_id,
        compiled=decision.compiled,
        rejected=decision.rejected,
        snapshots=tuple(_snapshot_dict(item) for item in snapshots),
    )


class _FrozenProbeAdapter(MusicProviderAdapter):
    def __init__(
        self, delegate: MusicProviderAdapter, snapshot: CapabilitySnapshot
    ):
        self.delegate = delegate
        self.provider_id = delegate.provider_id
        self.snapshot = snapshot

    def probe(self) -> CapabilitySnapshot:
        return self.snapshot

    def compile(self, request: SongRequest) -> dict:
        return self.delegate.compile(request)


def _snapshot_dict(snapshot: CapabilitySnapshot) -> dict:
    return {
        "provider_id": snapshot.provider_id,
        "availability": snapshot.availability.value,
        "capabilities": sorted(snapshot.capabilities),
        "cost_class": snapshot.cost_class,
        "runtime": snapshot.runtime,
        "evidence": snapshot.evidence,
    }
