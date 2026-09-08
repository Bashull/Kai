from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ActivationCheckpointStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    NEEDS_CANARY = "NEEDS_CANARY"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class ActivationCheckpointPlan:
    mode: str | None
    save_regions: tuple[str, ...] = field(default_factory=tuple)
    status: ActivationCheckpointStatus = ActivationCheckpointStatus.SUPPORTED
    rules: tuple[str, ...] = field(default_factory=tuple)
    canaries: tuple[str, ...] = field(default_factory=tuple)
    decisions: tuple[str, ...] = field(default_factory=tuple)


def plan_activation_checkpointing(request: dict[str, Any]) -> ActivationCheckpointPlan:
    mode = request.get("activation_checkpointing")
    if mode is None:
        return ActivationCheckpointPlan(None, decisions=("activation_checkpoint.none_explicit",))

    if mode in {"full", "selective"}:
        return ActivationCheckpointPlan(mode, decisions=(f"activation_checkpoint.{mode}",))

    if mode != "region_remat":
        return ActivationCheckpointPlan(
            mode,
            status=ActivationCheckpointStatus.UNSUPPORTED,
            rules=("activation_checkpoint.mode.invalid",),
        )

    if request.get("torchtitan_available") is not True:
        return ActivationCheckpointPlan(
            mode,
            status=ActivationCheckpointStatus.UNSUPPORTED,
            rules=("activation_checkpoint.region_remat.requires_torchtitan",),
        )

    if request.get("torch_remat_available") is not True:
        return ActivationCheckpointPlan(
            mode,
            status=ActivationCheckpointStatus.UNSUPPORTED,
            rules=("activation_checkpoint.region_remat.requires_torch_remat",),
        )

    if request.get("preserve_rng_state") is True:
        return ActivationCheckpointPlan(
            mode,
            status=ActivationCheckpointStatus.UNSUPPORTED,
            rules=("activation_checkpoint.region_remat.requires_explicit_rng_hooks",),
        )

    save_regions = tuple(request.get("activation_save_regions", ()))
    if request.get("region_remat_canary_passed") is not True:
        return ActivationCheckpointPlan(
            mode,
            save_regions=save_regions,
            status=ActivationCheckpointStatus.NEEDS_CANARY,
            rules=("activation_checkpoint.region_remat.experimental",),
            canaries=("torchtitan_region_remat",),
        )

    return ActivationCheckpointPlan(
        mode,
        save_regions=save_regions,
        decisions=("activation_checkpoint.region_remat_verified",),
    )
