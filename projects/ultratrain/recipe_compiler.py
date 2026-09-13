from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from .activation_checkpoint_policy import plan_activation_checkpointing


class RecipeBlocked(RuntimeError):
    def __init__(self, recipe: "CompiledRecipe") -> None:
        super().__init__(f"recipe is not executable: status={recipe.status}")
        self.recipe = recipe


@dataclass(frozen=True)
class CompiledRecipe:
    schema_version: str
    profile_id: str | None
    method: str | None
    training_engine: str | None
    kernel_backend: str | None
    status: str
    executable: bool
    training_args: dict[str, Any] = field(default_factory=dict)
    runtime_args: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, str] = field(default_factory=dict)
    rules: tuple[str, ...] = field(default_factory=tuple)
    canaries: tuple[str, ...] = field(default_factory=tuple)
    decisions: tuple[str, ...] = field(default_factory=tuple)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    return value.value if hasattr(value, "value") else value


def _status(value: Any) -> str:
    raw = str(_value(value) or "UNSUPPORTED")
    return raw if raw in {"SUPPORTED", "FALLBACK", "NEEDS_CANARY", "UNSUPPORTED"} else "UNSUPPORTED"


def _worst_status(*values: Any) -> str:
    rank = {"SUPPORTED": 0, "FALLBACK": 1, "NEEDS_CANARY": 2, "UNSUPPORTED": 3}
    statuses = [_status(value) for value in values]
    return max(statuses, key=rank.get, default="UNSUPPORTED")


def _unique(items: Any) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(item) for item in items if item))


def _plan_decisions(plan: Any) -> tuple[str, ...]:
    values = list(getattr(plan, "decisions", ()) or ())
    kernel = getattr(plan, "kernel", None)
    if kernel is not None:
        values.extend(getattr(kernel, "decisions", ()) or ())
    return _unique(values)


def compile_recipe(
    plan: Any,
    request: dict[str, Any],
    *,
    require_executable: bool = False,
) -> CompiledRecipe:
    source = deepcopy(request)
    runtime = getattr(plan, "runtime", None)
    kernel = getattr(plan, "kernel", None)
    long_context = getattr(plan, "long_context", None)
    method = _value(getattr(plan, "method", None))
    training_engine = getattr(runtime, "training_engine", None) if runtime is not None else None
    kernel_backend = getattr(kernel, "backend", None) if kernel is not None else None

    decisions = list(_plan_decisions(plan))
    rules = list(getattr(plan, "rules", ()) or ())
    canaries = list(getattr(plan, "canaries", ()) or ())
    training_args: dict[str, Any] = {}
    runtime_args: dict[str, Any] = {}
    environment: dict[str, str] = {}

    long_profile = dict(getattr(long_context, "profile", {}) or {}) if long_context is not None else {}
    if long_profile:
        loss_type = long_profile.get("loss_type")
        if loss_type is not None:
            if (
                loss_type == "chunked"
                and training_engine == "trl"
                and "long_context.loss.trl_113_tensorcore_fastpath" in decisions
            ):
                training_args["loss_type"] = "chunked_nll"
            else:
                training_args["loss_type"] = loss_type
        if long_profile.get("target_tokens") is not None:
            training_args["max_seq_length"] = int(long_profile["target_tokens"])
        if long_profile.get("parallelism") is not None:
            runtime_args["sequence_parallelism"] = long_profile["parallelism"]
        if long_profile.get("backend") is not None:
            runtime_args["distributed_backend"] = long_profile["backend"]
        if long_profile.get("expandable_segments") is True:
            environment["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

    if kernel_backend == "liger":
        training_args["use_liger_kernel"] = True
        if "kernel.liger.preference_frozen_weight_fastpath" in decisions:
            training_args["liger_preference_frozen_weight_fastpath"] = True

    if source.get("attention") is not None:
        training_args["attn_implementation"] = source["attention"]
    if source.get("peft") is not None:
        training_args["peft"] = deepcopy(source["peft"])

    activation = plan_activation_checkpointing(source)
    activation_status = _status(activation.status)
    rules.extend(activation.rules)
    canaries.extend(activation.canaries)
    decisions.extend(activation.decisions)
    if activation.mode is not None:
        training_args["activation_checkpointing"] = activation.mode
    if activation.mode == "region_remat":
        training_args["activation_save_regions"] = list(activation.save_regions)
        if activation_status == "SUPPORTED":
            training_args["region_remat_rng_mode"] = "explicit_hooks"

    if runtime is not None:
        if getattr(runtime, "rollout_provider", None) is not None:
            runtime_args["rollout_provider"] = runtime.rollout_provider
        if getattr(runtime, "teacher_provider", None) is not None:
            runtime_args["teacher_provider"] = runtime.teacher_provider

    runtime_boundary = source.get("capability_runtime")
    if isinstance(runtime_boundary, dict):
        for key in ("provider_id", "isolation", "requires_isolation", "conflicts", "license_boundary"):
            if key in runtime_boundary:
                runtime_args[key] = deepcopy(runtime_boundary[key])

    plan_status = _status(getattr(plan, "status", None))
    overall_status = _worst_status(plan_status, activation_status)
    executable = overall_status in {"SUPPORTED", "FALLBACK"} and training_engine is not None

    recipe = CompiledRecipe(
        schema_version="ultratrain.compiled_recipe/v1",
        profile_id=source.get("profile_id"),
        method=str(method) if method is not None else None,
        training_engine=training_engine,
        kernel_backend=kernel_backend,
        status=overall_status,
        executable=executable,
        training_args=training_args,
        runtime_args=runtime_args,
        environment=environment,
        rules=_unique(rules),
        canaries=_unique(canaries),
        decisions=_unique(decisions),
        provenance={
            "planner_status": plan_status,
            "activation_checkpoint_status": activation_status,
            "capability_schema_version": source.get("capability_schema_version"),
        },
    )
    if require_executable and not recipe.executable:
        raise RecipeBlocked(recipe)
    return recipe
