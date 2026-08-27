from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
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


class IntegrityStatus(str, Enum):
    VERIFIED = "VERIFIED"
    SIZE_MISMATCH = "SIZE_MISMATCH"
    HASH_MISMATCH = "HASH_MISMATCH"


@dataclass(frozen=True)
class IntegrityResult:
    status: IntegrityStatus
    expected_sha256: str
    actual_sha256: str
    expected_size_bytes: int
    actual_size_bytes: int

    @property
    def allow_promotion(self) -> bool:
        return self.status is IntegrityStatus.VERIFIED


def verify_artifact_bytes(ref: ArtifactRef, payload: bytes) -> IntegrityResult:
    actual_sha256 = hashlib.sha256(payload).hexdigest()
    actual_size = len(payload)
    if actual_size != ref.size_bytes:
        status = IntegrityStatus.SIZE_MISMATCH
    elif actual_sha256.lower() != ref.sha256.lower():
        status = IntegrityStatus.HASH_MISMATCH
    else:
        status = IntegrityStatus.VERIFIED
    return IntegrityResult(
        status=status,
        expected_sha256=ref.sha256,
        actual_sha256=actual_sha256,
        expected_size_bytes=ref.size_bytes,
        actual_size_bytes=actual_size,
    )


@dataclass(frozen=True)
class ModelVersionRef:
    model_id: str
    version_id: str
    run_id: str
    artifact: ArtifactRef

    def __post_init__(self) -> None:
        if not self.model_id:
            raise ValueError("model.model_id")
        if not self.version_id:
            raise ValueError("model.version_id")
        if not self.run_id:
            raise ValueError("model.run_id")


@dataclass(frozen=True)
class PromotionAlias:
    alias: str
    target_version_id: str

    def __post_init__(self) -> None:
        if not self.alias:
            raise ValueError("promotion.alias")
        if not self.target_version_id:
            raise ValueError("promotion.target_version_id")

    def rebind(self, target_version_id: str) -> "PromotionAlias":
        if not target_version_id:
            raise ValueError("promotion.target_version_id")
        return PromotionAlias(alias=self.alias, target_version_id=target_version_id)
