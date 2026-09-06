from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .long_context_policy import LongContextStatus, evaluate_long_context_profile


@dataclass(frozen=True)
class SmartPlan:
    profile: dict[str, Any]
    status: LongContextStatus
    rules: tuple[str, ...]
    canaries: tuple[str, ...]
    decisions: tuple[str, ...]


def _version_tuple(value: str | None) -> tuple[int, int, int] | None:
    if not value:
        return None
    parts = value.split('.')
    if len(parts) < 3 or not all(part.isdigit() for part in parts[:3]):
        return None
    return tuple(int(part) for part in parts[:3])


def _cp_available(profile: dict[str, Any]) -> bool:
    accelerate = _version_tuple(profile.get('accelerate'))
    return (
        profile.get('fsdp2_available') is True
        and accelerate is not None
        and accelerate >= (1, 11, 0)
        and profile.get('attention', 'sdpa') == 'sdpa'
        and profile.get('causal_attention', True) is True
    )


def _sp_available(profile: dict[str, Any]) -> bool:
    accelerate = _version_tuple(profile.get('accelerate'))
    deepspeed = _version_tuple(profile.get('deepspeed'))
    if not (
        profile.get('deepspeed_available') is True
        and accelerate is not None
        and accelerate >= (1, 12, 0)
        and deepspeed is not None
        and deepspeed >= (0, 18, 1)
    ):
        return False
    size = int(profile.get('parallelism_size', 1))
    kv_heads = profile.get('kv_heads')
    return kv_heads is None or size <= int(kv_heads)


def plan_long_context(request: dict[str, Any]) -> SmartPlan:
    profile = dict(request)
    decisions: list[str] = []
    target = int(profile.get('target_tokens', 0))

    if target >= 131_072 and 'loss_type' not in profile:
        profile['loss_type'] = 'chunked'
        decisions.append('long_context.loss.chunked_default')

    if target >= 1_000_000:
        if 'expandable_segments' not in profile:
            profile['expandable_segments'] = True
            decisions.append('long_context.cuda_allocator.expandable_segments_default')
        if 'parallelism' not in profile:
            if _cp_available(profile):
                profile['parallelism'] = 'cp'
                profile['backend'] = 'fsdp2'
                decisions.append('long_context.parallelism.cp_selected')
            elif _sp_available(profile):
                profile['parallelism'] = 'sp'
                profile['backend'] = 'deepspeed'
                decisions.append('long_context.parallelism.sp_selected')

    result = evaluate_long_context_profile(profile)
    return SmartPlan(
        profile=profile,
        status=result.status,
        rules=result.rules,
        canaries=result.canaries,
        decisions=tuple(decisions),
    )
