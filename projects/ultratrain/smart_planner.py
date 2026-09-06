from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .compatibility_core import CompatibilityResult, Decision, evaluate_profile
from .kernel_policy import KernelRoute, route_kernel
from .long_context_policy import LongContextStatus, evaluate_long_context_profile
from .method_selector import MethodSelection, TrainingMethod, select_training_method
from .runtime_policy import RuntimeRoute, route_runtime


@dataclass(frozen=True)
class SmartPlan:
    profile: dict[str, Any]
    status: LongContextStatus
    rules: tuple[str, ...]
    canaries: tuple[str, ...]
    decisions: tuple[str, ...]


@dataclass(frozen=True)
class TrainingSmartPlan:
    method: TrainingMethod | None
    method_selection: MethodSelection
    runtime: RuntimeRoute | None
    kernel: KernelRoute
    long_context: SmartPlan | None
    compatibility: CompatibilityResult | None
    status: Decision
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


def _to_decision(status: Any) -> Decision:
    value = status.value if hasattr(status, 'value') else str(status)
    if value == Decision.UNSUPPORTED.value:
        return Decision.UNSUPPORTED
    if value == Decision.NEEDS_CANARY.value:
        return Decision.NEEDS_CANARY
    if value == Decision.FALLBACK.value:
        return Decision.FALLBACK
    return Decision.SUPPORTED


def _worst_status(statuses: Iterable[Any]) -> Decision:
    rank = {
        Decision.SUPPORTED: 0,
        Decision.FALLBACK: 1,
        Decision.NEEDS_CANARY: 2,
        Decision.UNSUPPORTED: 3,
    }
    decisions = [_to_decision(status) for status in statuses]
    return max(decisions, key=rank.get, default=Decision.SUPPORTED)


def _unique(items: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item for item in items if item))


def _build_compatibility_profile(
    request: dict[str, Any],
    method: TrainingMethod,
    runtime: RuntimeRoute,
    long_context: SmartPlan | None,
) -> dict[str, Any]:
    profile = dict(request.get('compatibility_profile', {}))
    profile.setdefault('profile_id', request.get('profile_id'))

    packages = dict(request.get('packages', {}))
    if request.get('accelerate') is not None:
        packages.setdefault('accelerate', request['accelerate'])
    if request.get('transformers_version') is not None:
        packages.setdefault('transformers', request['transformers_version'])
    profile['packages'] = packages

    trl = dict(request.get('trl', {}))
    if request.get('trl_version') is not None:
        trl.setdefault('version', request['trl_version'])
    if method is TrainingMethod.DISTILLATION and request.get('async_distillation') is True:
        trl['async_distillation'] = True
    if runtime.rollout_provider == 'vllm' or runtime.teacher_provider == 'vllm':
        trl['vllm_server_mode'] = True
        if request.get('trl_vllm_canary_passed') is True:
            trl['vllm_028_canary_passed'] = True
    profile['trl'] = trl

    runtime_profile = dict(request.get('runtime', {}))
    if runtime.rollout_provider == 'vllm' or runtime.teacher_provider == 'vllm':
        runtime_profile['vllm'] = True
        runtime_profile['vllm_version'] = request.get('vllm_version')
        runtime_profile['vllm_canary_passed'] = request.get('vllm_canary_passed') is True
    profile['runtime'] = runtime_profile

    distributed = dict(request.get('distributed', {}))
    if long_context is not None:
        parallelism = long_context.profile.get('parallelism')
        if parallelism == 'cp':
            distributed['enabled'] = True
            distributed['context_parallelism'] = True
            distributed['fsdp_version'] = 2
        elif parallelism == 'sp':
            distributed['enabled'] = True
    profile['distributed'] = distributed

    for key in ('tracking', 'transformers', 'peft', 'hardware', 'megatron', 'ray', 'dataset', 'export', 'hub'):
        if key in request:
            profile[key] = dict(request[key])
    return profile


def plan_training(request: dict[str, Any]) -> TrainingSmartPlan:
    method_selection = select_training_method(request)
    kernel = route_kernel(request)
    long_context = plan_long_context(request) if request.get('target_tokens') is not None else None

    runtime: RuntimeRoute | None = None
    compatibility: CompatibilityResult | None = None
    statuses: list[Any] = [method_selection.status, kernel.status]
    rules: list[str] = [*method_selection.rules, *kernel.rules]
    canaries: list[str] = [*method_selection.canaries, *kernel.canaries]
    decisions: list[str] = [*method_selection.decisions, *kernel.decisions]

    if long_context is not None:
        statuses.append(long_context.status)
        rules.extend(long_context.rules)
        canaries.extend(long_context.canaries)
        decisions.extend(long_context.decisions)

    if method_selection.method is not None:
        runtime = route_runtime(method_selection.method, request)
        statuses.append(runtime.status)
        rules.extend(runtime.rules)
        canaries.extend(runtime.canaries)
        decisions.extend(runtime.decisions)

        compatibility_profile = _build_compatibility_profile(
            request,
            method_selection.method,
            runtime,
            long_context,
        )
        compatibility = evaluate_profile(compatibility_profile)
        statuses.append(compatibility.status)
        rules.extend(compatibility.rules)
        canaries.extend(compatibility.canaries)

    return TrainingSmartPlan(
        method=method_selection.method,
        method_selection=method_selection,
        runtime=runtime,
        kernel=kernel,
        long_context=long_context,
        compatibility=compatibility,
        status=_worst_status(statuses),
        rules=_unique(rules),
        canaries=_unique(canaries),
        decisions=_unique(decisions),
    )
