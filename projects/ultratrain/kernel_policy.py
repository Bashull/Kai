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


def _version_tuple(value: str | None) -> tuple[int, int, int] | None:
    if not value:
        return None
    parts = value.split(".")
    if len(parts) < 3 or not all(part.isdigit() for part in parts[:3]):
        return None
    return tuple(int(part) for part in parts[:3])


def _liger_083_or_newer(request: dict[str, Any]) -> bool:
    version = _version_tuple(request.get("liger_version"))
    return version is not None and version >= (0, 8, 3)


def _is_resolved_dpo_request(request: dict[str, Any]) -> bool:
    explicit = request.get("method")
    if explicit is not None:
        return str(explicit).lower() == "dpo"
    return (
        request.get("preference_pairs") is True
        and request.get("reward_signal") is not True
        and request.get("teacher_available") is not True
    )


def _is_distillation_request(request: dict[str, Any]) -> bool:
    explicit = request.get("method")
    if explicit is not None:
        return str(explicit).lower() == "distillation"
    return (
        request.get("teacher_available") is True
        and request.get("preference_pairs") is not True
        and request.get("reward_signal") is not True
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

    dsl = request.get("liger_dsl_backend")
    if (
        _liger_083_or_newer(request)
        and dsl in {"triton", "cutedsl", "cutile"}
        and request.get("liger_dsl_backend_available") is True
        and request.get("liger_dsl_canary_passed") is True
    ):
        decisions.append(f"kernel.liger.dsl.{dsl}_verified")

    if (
        _liger_083_or_newer(request)
        and _is_distillation_request(request)
        and request.get("liger_fused_linear_kl_available") is True
        and request.get("liger_fused_linear_kl_canary_passed") is True
    ):
        decisions.append("kernel.liger.distillation.fused_linear_kl_verified")
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
