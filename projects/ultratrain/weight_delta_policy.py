from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class WeightDeltaStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    NEEDS_CANARY = "NEEDS_CANARY"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class WeightDeltaRoute:
    transport: str | None
    status: WeightDeltaStatus
    rules: tuple[str, ...] = field(default_factory=tuple)
    canaries: tuple[str, ...] = field(default_factory=tuple)
    decisions: tuple[str, ...] = field(default_factory=tuple)


def _version_tuple(value: str | None) -> tuple[int, int, int] | None:
    if not value:
        return None
    parts = value.split(".")
    if len(parts) < 3 or not all(part.isdigit() for part in parts[:3]):
        return None
    return tuple(int(part) for part in parts[:3])


def select_weight_delta_transport(request: dict[str, Any]) -> WeightDeltaRoute:
    version = _version_tuple(request.get("vllm_version"))
    explicit = request.get("weight_delta_transport")

    if explicit is not None and explicit not in {"full_nccl", "sparse_nccl", "sharded_rdt"}:
        return WeightDeltaRoute(explicit, WeightDeltaStatus.UNSUPPORTED, ("weight_delta.transport.invalid",))

    if explicit == "sharded_rdt" or (
        explicit is None
        and version is not None
        and version >= (0, 29, 0)
        and request.get("sharded_rdt_available") is True
        and (request.get("tensor_parallel_size", 1) > 1 or request.get("expert_parallel_size", 1) > 1)
    ):
        if version is None or version < (0, 29, 0):
            return WeightDeltaRoute("sharded_rdt", WeightDeltaStatus.UNSUPPORTED, ("weight_delta.sharded_rdt.requires_vllm_029",))
        if request.get("sharded_rdt_available") is not True:
            return WeightDeltaRoute("sharded_rdt", WeightDeltaStatus.UNSUPPORTED, ("weight_delta.sharded_rdt.capability_required",))
        if request.get("sharded_rdt_canary_passed") is not True:
            return WeightDeltaRoute(
                "sharded_rdt",
                WeightDeltaStatus.NEEDS_CANARY,
                ("weight_delta.sharded_rdt.correctness_required",),
                ("vllm_sharded_rdt_weight_sync",),
            )
        return WeightDeltaRoute("sharded_rdt", WeightDeltaStatus.SUPPORTED, decisions=("weight_delta.vllm029.sharded_rdt",))

    if explicit == "sparse_nccl" or (
        explicit is None
        and version is not None
        and version >= (0, 29, 0)
        and request.get("sparse_nccl_available") is True
    ):
        if version is None or version < (0, 29, 0):
            return WeightDeltaRoute("sparse_nccl", WeightDeltaStatus.UNSUPPORTED, ("weight_delta.sparse_nccl.requires_vllm_029",))
        if request.get("sparse_nccl_available") is not True:
            return WeightDeltaRoute("sparse_nccl", WeightDeltaStatus.UNSUPPORTED, ("weight_delta.sparse_nccl.capability_required",))
        if request.get("sparse_nccl_canary_passed") is not True:
            return WeightDeltaRoute(
                "sparse_nccl",
                WeightDeltaStatus.NEEDS_CANARY,
                ("weight_delta.sparse_nccl.correctness_required",),
                ("vllm_sparse_nccl_weight_sync",),
            )
        return WeightDeltaRoute("sparse_nccl", WeightDeltaStatus.SUPPORTED, decisions=("weight_delta.vllm029.sparse_nccl",))

    return WeightDeltaRoute("full_nccl", WeightDeltaStatus.SUPPORTED, decisions=("weight_delta.full_nccl.safe_default",))
