from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any


class CapabilityState(str, Enum):
    UNKNOWN = "UNKNOWN"
    DECLARED = "DECLARED"
    PROBED = "PROBED"
    CANARY = "CANARY"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class PackageIdentity:
    name: str
    version: str
    source: str = "unknown"
    build: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("package name is required")
        if not self.version.strip():
            raise ValueError(f"exact version is required for package {self.name!r}")
        if not self.source.strip():
            raise ValueError("package identity source is required")


@dataclass(frozen=True)
class CapabilityEvidence:
    capability: str
    state: CapabilityState
    evidence: str = ""
    details: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.capability.strip():
            raise ValueError("capability name is required")
        if self.state in {CapabilityState.PROBED, CapabilityState.CANARY} and not self.evidence.strip():
            raise ValueError(f"{self.state.value} capability evidence requires an evidence reference")


@dataclass(frozen=True)
class RuntimeProviderDescriptor:
    provider_id: str
    isolation: str
    packages: tuple[PackageIdentity, ...] = field(default_factory=tuple)
    capabilities: tuple[CapabilityEvidence, ...] = field(default_factory=tuple)
    conflicts: tuple[str, ...] = field(default_factory=tuple)
    license_boundary: str | None = None

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("runtime provider_id is required")
        if self.isolation not in {"shared", "process", "container", "remote"}:
            raise ValueError(f"unsupported isolation mode: {self.isolation!r}")
        if self.conflicts and self.isolation == "shared":
            raise ValueError("a runtime with dependency conflicts must be isolated")

    @property
    def requires_isolation(self) -> bool:
        return bool(self.conflicts) or self.isolation != "shared"

    def capability_state(self, capability: str) -> CapabilityState:
        rank = {
            CapabilityState.UNKNOWN: 0,
            CapabilityState.DECLARED: 1,
            CapabilityState.PROBED: 2,
            CapabilityState.CANARY: 3,
            CapabilityState.UNSUPPORTED: 4,
        }
        states = [item.state for item in self.capabilities if item.capability == capability]
        return max(states, key=rank.get, default=CapabilityState.UNKNOWN)


@dataclass(frozen=True)
class GPUDevice:
    ordinal: int
    name: str
    vram_bytes: int
    backend: str = "cuda"

    def __post_init__(self) -> None:
        if self.ordinal < 0:
            raise ValueError("GPU ordinal cannot be negative")
        if not self.name.strip():
            raise ValueError("GPU name is required")
        if self.vram_bytes < 0:
            raise ValueError("GPU vram_bytes cannot be negative")
        if not self.backend.strip():
            raise ValueError("GPU backend is required")


@dataclass(frozen=True)
class HardwareSnapshot:
    platform: str
    ram_bytes: int
    cpu: str | None = None
    gpus: tuple[GPUDevice, ...] = field(default_factory=tuple)
    source: str = "hardware-doctor"

    def __post_init__(self) -> None:
        if not self.platform.strip():
            raise ValueError("hardware platform is required")
        if self.ram_bytes < 0:
            raise ValueError("ram_bytes cannot be negative")
        if not self.source.strip():
            raise ValueError("hardware evidence source is required")


@dataclass(frozen=True)
class MemoryEstimate:
    bytes_required: int
    basis: str
    confidence: float
    assumptions: tuple[str, ...] = field(default_factory=tuple)
    evidence: str | None = None

    def __post_init__(self) -> None:
        if self.bytes_required < 0:
            raise ValueError("bytes_required cannot be negative")
        if self.basis not in {"measured", "estimated"}:
            raise ValueError("basis must be 'measured' or 'estimated'")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class ModelCapabilityProfile:
    model_id: str
    family: str
    baseline: dict[str, Any] = field(default_factory=dict)
    deltas: dict[str, Any] = field(default_factory=dict)
    evidence: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise ValueError("model_id is required")
        if not self.family.strip():
            raise ValueError("model family is required")

    def resolved_capabilities(self) -> dict[str, Any]:
        resolved = dict(self.baseline)
        resolved.update(self.deltas)
        return resolved


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


@dataclass(frozen=True)
class PlannerCapabilityInput:
    schema_version: str
    runtime: RuntimeProviderDescriptor
    hardware: HardwareSnapshot
    model: ModelCapabilityProfile
    memory: MemoryEstimate | None = None
    evidence: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.schema_version.strip():
            raise ValueError("schema_version is required")

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
