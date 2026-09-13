from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from .async_distillation_policy import AsyncDistillationPlan, AsyncDistillationStatus


class AsyncDistillationAdapterError(ValueError):
    pass


@dataclass(frozen=True)
class AsyncTRLTrainerRecipe:
    method: str
    trainer_class: str
    config_class: str
    config_kwargs: dict[str, Any] = field(default_factory=dict)
    runtime_args: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, str] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)


def adapt_trl_async_distillation(
    recipe: Any,
    plan: AsyncDistillationPlan,
    *,
    trl_version: str,
) -> AsyncTRLTrainerRecipe:
    if trl_version != "1.13.0":
        raise AsyncDistillationAdapterError("adapter is pinned to exact TRL 1.13.0 identity")
    if str(getattr(recipe, "method", "")).lower() != "distillation":
        raise AsyncDistillationAdapterError("distillation compiled recipe is required")
    if getattr(recipe, "training_engine", None) != "trl":
        raise AsyncDistillationAdapterError("TRL training engine is required")
    if not getattr(recipe, "executable", False):
        raise AsyncDistillationAdapterError("compiled recipe must be executable")

    runtime_args = deepcopy(getattr(recipe, "runtime_args", {}) or {})
    if runtime_args.get("teacher_provider") != "vllm":
        raise AsyncDistillationAdapterError("planner must route async distillation teacher through vllm")

    if plan.status is not AsyncDistillationStatus.SUPPORTED:
        raise AsyncDistillationAdapterError(f"async distillation policy is not promotable: {plan.status.value}")
    if plan.weight_delta_transport != "full_nccl":
        raise AsyncDistillationAdapterError("TRL 1.13 upstream async trainer is only mapped to full_nccl")

    runtime_args["async_distillation"] = True
    runtime_args["weight_delta_transport"] = plan.weight_delta_transport

    return AsyncTRLTrainerRecipe(
        method="distillation",
        trainer_class=plan.trainer_class,
        config_class="trl.experimental.async_distillation.AsyncDistillationConfig",
        config_kwargs=deepcopy(plan.config_kwargs),
        runtime_args=runtime_args,
        environment=deepcopy(getattr(recipe, "environment", {}) or {}),
        provenance={
            "trl_version": trl_version,
            "policy_decisions": list(plan.decisions),
            "adapter": "trl_async_distillation/v1",
        },
    )
