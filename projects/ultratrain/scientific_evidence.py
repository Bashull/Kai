from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


def _require_sha256(value: str, field_name: str) -> None:
    if len(value) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in value):
        raise ValueError(field_name)


@dataclass(frozen=True)
class ArtifactRef:
    uri: str
    sha256: str
    size_bytes: int
    media_type: str

    def __post_init__(self) -> None:
        if not self.uri:
            raise ValueError("artifact.uri")
        _require_sha256(self.sha256, "artifact.sha256")
        if self.size_bytes < 0:
            raise ValueError("artifact.size_bytes")

@dataclass(frozen=True)
class DatasetRef:
    dataset_id: str
    revision: str | None = None

    def __post_init__(self) -> None:
        if not self.dataset_id:
            raise ValueError("dataset.dataset_id")


@dataclass(frozen=True)
class ScientificRunEnvelope:
    run_id: str
    recipe_digest: str
    datasets: tuple[DatasetRef, ...] = field(default_factory=tuple)
    artifacts: tuple[ArtifactRef, ...] = field(default_factory=tuple)
    parent_run_id: str | None = None
    child_run_ids: tuple[str, ...] = field(default_factory=tuple)
    hardware_profile: dict[str, Any] = field(default_factory=dict)
    runtime_profile: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    evals: dict[str, Any] = field(default_factory=dict)
    provider_refs: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("run.run_id")
        _require_sha256(self.recipe_digest, "run.recipe_digest")

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)
