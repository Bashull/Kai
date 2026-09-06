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
        return KernelRoute("liger", KernelStatus.SUPPORTED, decisions=("kernel.liger.explicit_verified",))

    if request.get("prefer_fused_kernels") is True and request.get("liger_available") is True:
        if request.get("liger_canary_passed") is True:
            return KernelRoute("liger", KernelStatus.SUPPORTED, decisions=("kernel.liger.auto_promoted",))
        return KernelRoute("sdpa", KernelStatus.SUPPORTED, decisions=("kernel.liger_not_promoted_without_canary",))
    return KernelRoute("sdpa", KernelStatus.SUPPORTED, decisions=("kernel.sdpa.safe_default",))
