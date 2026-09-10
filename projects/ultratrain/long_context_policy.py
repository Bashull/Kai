from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LongContextStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    NEEDS_CANARY = "NEEDS_CANARY"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class LongContextResult:
    status: LongContextStatus
    rules: tuple[str, ...] = field(default_factory=tuple)
    canaries: tuple[str, ...] = field(default_factory=tuple)


def _version_tuple(value: str | None) -> tuple[int, int, int] | None:
    if not value:
        return None
    parts = value.split(".")
    if len(parts) < 3 or not all(part.isdigit() for part in parts[:3]):
        return None
    return tuple(int(part) for part in parts[:3])


def _result(status: LongContextStatus, rule: str, canary: str | None = None) -> LongContextResult:
    return LongContextResult(status=status, rules=(rule,), canaries=(canary,) if canary else ())


def evaluate_long_context_profile(profile: dict[str, Any]) -> LongContextResult:
    target = int(profile.get("target_tokens", 0))
    if target <= 0:
        return _result(LongContextStatus.UNSUPPORTED, "long_context.target_tokens.required")

    native = profile.get("native_context_tokens")
    if native is not None and target > int(native) and not profile.get("position_extension_strategy"):
        return _result(LongContextStatus.NEEDS_CANARY, "long_context.position_extension.required", "long_context_position_extension")

    if profile.get("loss_type") == "nll" and target >= 131_072:
        return _result(LongContextStatus.NEEDS_CANARY, "long_context.chunked_loss.preferred", "long_context_loss_memory")

    if profile.get("activation_offload"):
        transformers_version = _version_tuple(profile.get("transformers_version"))
        if transformers_version is None:
            return _result(
                LongContextStatus.NEEDS_CANARY,
                "long_context.activation_offload.transformers_identity",
                "transformers_activation_offload_identity",
            )
        if transformers_version < (5, 16, 0):
            return _result(LongContextStatus.UNSUPPORTED, "long_context.activation_offload.requires_transformers_516")

    parallelism = profile.get("parallelism")
    backend = profile.get("backend")
    accelerate = _version_tuple(profile.get("accelerate"))
    trl_version = _version_tuple(profile.get("trl_version"))

    if parallelism == "cp":
        if backend != "fsdp2":
            return _result(LongContextStatus.UNSUPPORTED, "long_context.cp.requires_fsdp2")
        if accelerate is None or accelerate < (1, 11, 0):
            return _result(LongContextStatus.UNSUPPORTED, "long_context.cp.requires_accelerate_111")
        if profile.get("model_supports_context_parallel") is False:
            return _result(LongContextStatus.UNSUPPORTED, "long_context.cp.model_unsupported")
        attention = profile.get("attention", "sdpa")
        if attention != "sdpa" or profile.get("causal_attention", True) is not True:
            return _result(LongContextStatus.UNSUPPORTED, "long_context.cp.requires_causal_sdpa")

    if parallelism == "sp":
        if backend != "deepspeed":
            return _result(LongContextStatus.UNSUPPORTED, "long_context.sp.requires_deepspeed")
        if accelerate is None or accelerate < (1, 12, 0):
            return _result(LongContextStatus.UNSUPPORTED, "long_context.sp.requires_accelerate_112")
        deepspeed = _version_tuple(profile.get("deepspeed"))
        required_deepspeed = (0, 18, 6) if trl_version is not None and trl_version >= (1, 13, 0) else (0, 18, 1)
        if deepspeed is None or deepspeed < required_deepspeed:
            rule = (
                "long_context.sp.trl_113_requires_deepspeed_0186"
                if required_deepspeed == (0, 18, 6)
                else "long_context.sp.requires_deepspeed_0181"
            )
            return _result(LongContextStatus.UNSUPPORTED, rule)
        size = int(profile.get("parallelism_size", 1))
        kv_heads = profile.get("kv_heads")
        if kv_heads is not None and size > int(kv_heads):
            return _result(LongContextStatus.UNSUPPORTED, "long_context.sp.limited_by_kv_heads")

    if target >= 1_000_000:
        if parallelism not in {"cp", "sp"}:
            return _result(LongContextStatus.NEEDS_CANARY, "long_context.million_tokens.requires_sequence_sharding", "million_token_capacity")
        if not profile.get("expandable_segments"):
            return _result(LongContextStatus.NEEDS_CANARY, "long_context.cuda_allocator.expandable_segments", "cuda_allocator_fragmentation")

    return _result(LongContextStatus.SUPPORTED, "long_context.profile_supported")
