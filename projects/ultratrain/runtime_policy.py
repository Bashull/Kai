from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .method_selector import TrainingMethod


class RuntimeStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    NEEDS_CANARY = "NEEDS_CANARY"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class RuntimeRoute:
    training_engine: str | None
    rollout_provider: str | None
    teacher_provider: str | None
    status: RuntimeStatus
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


def _secure_vllm(request: dict[str, Any]) -> bool:
    version = _version_tuple(request.get("vllm_version"))
    return request.get("vllm_available") is True and version is not None and version >= (0, 28, 0)


def _engine_for_supervised(request: dict[str, Any]) -> RuntimeRoute:
    explicit = request.get("training_engine")
    if explicit is not None:
        if explicit not in {"trl", "transformers"}:
            return RuntimeRoute(None, None, None, RuntimeStatus.UNSUPPORTED, ("runtime.engine.invalid",))
        if request.get(f"{explicit}_available") is not True:
            return RuntimeRoute(explicit, None, None, RuntimeStatus.UNSUPPORTED, (f"runtime.engine.{explicit}_unavailable",))
        return RuntimeRoute(explicit, None, None, RuntimeStatus.SUPPORTED, decisions=("runtime.engine.explicit",))
    if request.get("trl_available") is True:
        return RuntimeRoute("trl", None, None, RuntimeStatus.SUPPORTED, decisions=("runtime.engine.trl_selected",))
    if request.get("transformers_available") is True:
        return RuntimeRoute("transformers", None, None, RuntimeStatus.SUPPORTED, decisions=("runtime.engine.transformers_fallback",))
    return RuntimeRoute(None, None, None, RuntimeStatus.UNSUPPORTED, ("runtime.engine.none_available",))


def route_runtime(method: TrainingMethod, request: dict[str, Any]) -> RuntimeRoute:
    if method in {TrainingMethod.SFT, TrainingMethod.DPO}:
        return _engine_for_supervised(request)

    if request.get("trl_available") is not True:
        return RuntimeRoute(None, None, None, RuntimeStatus.UNSUPPORTED, ("runtime.trl.required",))

    if method is TrainingMethod.GRPO:
        explicit = request.get("rollout_provider")
        if explicit is not None:
            if explicit == "trl_inprocess":
                return RuntimeRoute("trl", explicit, None, RuntimeStatus.SUPPORTED, decisions=("runtime.rollout.explicit",))
            if explicit != "vllm":
                return RuntimeRoute("trl", explicit, None, RuntimeStatus.UNSUPPORTED, ("runtime.rollout.invalid",))
            if not _secure_vllm(request):
                return RuntimeRoute("trl", "vllm", None, RuntimeStatus.UNSUPPORTED, ("runtime.vllm.security_floor_028",))
            if request.get("vllm_canary_passed") is not True:
                return RuntimeRoute("trl", "vllm", None, RuntimeStatus.NEEDS_CANARY, ("runtime.vllm.canary",), ("vllm_runtime",))
            return RuntimeRoute("trl", "vllm", None, RuntimeStatus.SUPPORTED, decisions=("runtime.rollout.explicit",))

        if _secure_vllm(request) and request.get("vllm_canary_passed") is True:
            return RuntimeRoute("trl", "vllm", None, RuntimeStatus.SUPPORTED, decisions=("runtime.rollout.vllm_selected",))
        return RuntimeRoute("trl", "trl_inprocess", None, RuntimeStatus.SUPPORTED, decisions=("runtime.rollout.inprocess_safe_default",))

    if method is TrainingMethod.DISTILLATION:
        teacher = request.get("teacher_provider")
        teacher_available = request.get("teacher_available") is True or teacher is not None
        if not teacher_available:
            return RuntimeRoute("trl", None, None, RuntimeStatus.UNSUPPORTED, ("runtime.distillation.teacher_required",))
        if request.get("async_distillation") is True:
            teacher = "vllm"
            if not _secure_vllm(request):
                return RuntimeRoute("trl", None, teacher, RuntimeStatus.UNSUPPORTED, ("runtime.vllm.security_floor_028",))
            if request.get("vllm_canary_passed") is not True:
                return RuntimeRoute("trl", None, teacher, RuntimeStatus.NEEDS_CANARY, ("runtime.vllm.canary",), ("vllm_runtime",))
            return RuntimeRoute("trl", None, teacher, RuntimeStatus.SUPPORTED, decisions=("runtime.teacher.vllm_async",))
        return RuntimeRoute("trl", None, teacher or "external", RuntimeStatus.SUPPORTED, decisions=("runtime.teacher.external",))

    return RuntimeRoute(None, None, None, RuntimeStatus.UNSUPPORTED, ("runtime.method.unsupported",))
