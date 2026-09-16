"""Deterministic FREE-FIRST capability registry."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Mapping


class Availability(str, Enum):
    UNKNOWN = "UNKNOWN"
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class CostClass(IntEnum):
    LOCAL = 0
    OPEN = 1
    INCLUDED = 2
    PAID = 3


@dataclass(frozen=True, slots=True)
class WorkerCapability:
    worker_id: str
    capabilities: frozenset[str]
    locality: str
    cost_class: CostClass
    availability: Availability
    estimated_cost_eur: float
    license_notes: str = ""
    metadata: Mapping[str, str] = field(default_factory=dict)


class CapabilityRegistry:
    def __init__(self) -> None:
        self._workers: dict[str, WorkerCapability] = {}

    def register(self, worker: WorkerCapability) -> None:
        if worker.estimated_cost_eur < 0:
            raise ValueError("estimated_cost_eur cannot be negative")
        self._workers[worker.worker_id] = worker

    def candidates(self, capability: str, max_cost_eur: float) -> list[WorkerCapability]:
        if max_cost_eur < 0:
            return []
        matches = [
            worker
            for worker in self._workers.values()
            if capability in worker.capabilities
            and worker.availability is Availability.AVAILABLE
            and worker.estimated_cost_eur <= max_cost_eur
        ]
        return sorted(
            matches,
            key=lambda worker: (
                int(worker.cost_class),
                worker.estimated_cost_eur,
                worker.worker_id,
            ),
        )

    def all(self) -> list[WorkerCapability]:
        return sorted(self._workers.values(), key=lambda worker: worker.worker_id)


def default_cell000_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    registry.register(WorkerCapability(
        "github-actions", frozenset({"python.test", "python.compile"}),
        "cloud", CostClass.INCLUDED, Availability.UNKNOWN, 0.0,
    ))
    registry.register(WorkerCapability(
        "termux", frozenset({"python.test", "ffmpeg", "shell"}),
        "local", CostClass.LOCAL, Availability.UNKNOWN, 0.0,
    ))
    registry.register(WorkerCapability(
        "pc", frozenset({"python.test", "shell", "blender"}),
        "local", CostClass.LOCAL, Availability.UNKNOWN, 0.0,
    ))
    registry.register(WorkerCapability(
        "hf-jobs", frozenset({"gpu.burst", "cpu.burst"}),
        "cloud", CostClass.INCLUDED, Availability.UNKNOWN, 0.0,
        license_notes="Availability and billing must be probed at runtime.",
    ))
    return registry
