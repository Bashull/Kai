from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class KernelStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    NEEDS_CANARY = "NEEDS_CANARY"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class KernelRoute:
    backend: str | None
    status: KernelStatus
    rules: tuple[str, ...] = field(default_factory=tuple)
    canaries: tuple[str, ...] = field(default_factory=tuple)
    decisions: tuple[str, ...] = field(default_factory=tuple)


def _is_resolved_dpo_request(request: dict[str, Any]) -> bool:
    explicit = request.get("method")
    if explicit is not None:
        return str(explicit).lower() == "dpo"
    return (
        request.get("preference_pairs") is True
        and request.get("reward_signal") is not True
        and request.get("teacher_available") is not True
    )


def _peft_enabled(request: dict[str, Any]) -> bool:
    if request.get("peft_enabled") is True:
        return True
    peft = request.get("peft", {})
    return peft.get("lora") is True or peft.get("qlora_4bit") is True


def _verified_liger_decisions(request: dict[str, Any], base: str) -> tuple[str, ...]:
    decisions = [base]
    if (
        _is_resolved_dpo_request(request)
        and _peft_enabled(request)
        and request.get("preference_head_frozen") is True
        and request.get("liger_preference_frozen_weight_fastpath") is True
    ):
        decisions.append("kernel.liger.preference_frozen_weight_fastpath")
    return tuple(decisions)


def route_kernel(request: dict[str, Any]) -> KernelRoute:
    explicit = request.get("kernel_preference")
    if explicit is not None:
        if explicit == "sdpa":
            return KernelRoute("sdpa", KernelStatus.SUPPORTED, decisions=("kernel.sdpa.explicit",))
        if explicit != "liger":
            return KernelRoute(explicit, KernelStatus.UNSUPPORTED, ("kernel.preference.invalid",))
        if request.get("liger_available") is not True:
            return KernelRoute("liger", KernelStatus.UNSUPPORTED, ("kernel.liger.unavailable",))
        if request.get("liger_canary_passed") is not True:
            return KernelRoute("liger", KernelStatus.NEEDS_CANARY, ("kernel.liger.correctness_required",), ("liger_correctness",))
        return KernelRoute("liger", KernelStatus.SUPPORTED, decisions=_verified_liger_decisions(request, "kernel.liger.explicit_verified"))

    if request.get("prefer_fused_kernels") is True and request.get("liger_available") is True:
        if request.get("liger_canary_passed") is True:
            return KernelRoute("liger", KernelStatus.SUPPORTED, decisions=_verified_liger_decisions(request, "kernel.liger.auto_promoted"))
        return KernelRoute("sdpa", KernelStatus.SUPPORTED, decisions=("kernel.liger_not_promoted_without_canary",))
    return KernelRoute("sdpa", KernelStatus.SUPPORTED, decisions=("kernel.sdpa.safe_default",))
