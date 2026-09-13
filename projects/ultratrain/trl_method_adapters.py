from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


class TRLAdapterError(ValueError):
    pass


@dataclass(frozen=True)
class TRLTrainerRecipe:
    method: str
    config_class: str
    config_kwargs: dict[str, Any] = field(default_factory=dict)
    runtime_args: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, str] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)


def _copy_if_present(source: dict[str, Any], destination: dict[str, Any], source_key: str, target_key: str | None = None) -> None:
    if source_key in source:
        destination[target_key or source_key] = deepcopy(source[source_key])


def _require_trl_113(recipe: Any, trl_version: str | None) -> None:
    if getattr(recipe, "training_engine", None) != "trl":
        raise TRLAdapterError("TRL adapter requires a TRL training engine")
    if not getattr(recipe, "executable", False):
        raise TRLAdapterError("non-executable compiled recipe cannot be materialized")
    if trl_version != "1.13.0":
        raise TRLAdapterError("adapter is pinned to exact TRL 1.13.0 identity")


def _base_config(recipe: Any, request: dict[str, Any]) -> dict[str, Any]:
    args = dict(getattr(recipe, "training_args", {}) or {})
    config: dict[str, Any] = {}
    if "max_seq_length" in args:
        config["max_length"] = int(args["max_seq_length"])
    if "use_liger_kernel" in args:
        config["use_liger_kernel"] = bool(args["use_liger_kernel"])
    if "attn_implementation" in args:
        config["model_init_kwargs"] = {"attn_implementation": args["attn_implementation"]}
    if request.get("activation_offloading") is not None:
        config["activation_offloading"] = bool(request["activation_offloading"])
    return config


def adapt_trl_sft(recipe: Any, request: dict[str, Any], *, trl_version: str) -> TRLTrainerRecipe:
    _require_trl_113(recipe, trl_version)
    if str(getattr(recipe, "method", "")).lower() != "sft":
        raise TRLAdapterError("SFT adapter requires an SFT compiled recipe")

    args = dict(getattr(recipe, "training_args", {}) or {})
    config = _base_config(recipe, request)
    if args.get("loss_type") == "chunked_nll" and args.get("use_liger_kernel") is True:
        raise TRLAdapterError("TRL 1.13 SFT chunked_nll is incompatible with use_liger_kernel=True")

    if "loss_type" in args:
        config["loss_type"] = args["loss_type"]
    for key in (
        "packing",
        "packing_strategy",
        "assistant_only_loss",
        "completion_only_loss",
        "dataset_text_field",
        "dataset_num_proc",
        "shuffle_dataset",
        "eval_packing",
        "pad_to_multiple_of",
    ):
        _copy_if_present(request, config, key)

    if request.get("padding_free") is not None:
        config["padding_free"] = bool(request["padding_free"])

    return TRLTrainerRecipe(
        method="sft",
        config_class="trl.SFTConfig",
        config_kwargs=config,
        runtime_args=deepcopy(getattr(recipe, "runtime_args", {}) or {}),
        environment=deepcopy(getattr(recipe, "environment", {}) or {}),
        provenance={"trl_version": trl_version, "source_recipe_schema": getattr(recipe, "schema_version", None)},
    )


def adapt_trl_dpo(recipe: Any, request: dict[str, Any], *, trl_version: str) -> TRLTrainerRecipe:
    _require_trl_113(recipe, trl_version)
    if str(getattr(recipe, "method", "")).lower() != "dpo":
        raise TRLAdapterError("DPO adapter requires a DPO compiled recipe")

    config = _base_config(recipe, request)
    if request.get("padding_free") is True:
        raise TRLAdapterError("TRL 1.13 DPO padding_free is temporarily unavailable")

    if "dpo_loss_type" in request:
        value = request["dpo_loss_type"]
        config["loss_type"] = list(value) if isinstance(value, (list, tuple)) else [str(value)]
    for source_key, target_key in (
        ("dpo_loss_weights", "loss_weights"),
        ("dpo_beta", "beta"),
        ("dpo_precompute_ref_log_probs", "precompute_ref_log_probs"),
        ("dpo_precompute_ref_batch_size", "precompute_ref_batch_size"),
        ("dpo_label_smoothing", "label_smoothing"),
        ("dpo_f_divergence_type", "f_divergence_type"),
        ("dpo_sync_ref_model", "sync_ref_model"),
        ("dpo_ref_model_mixup_alpha", "ref_model_mixup_alpha"),
        ("dpo_ref_model_sync_steps", "ref_model_sync_steps"),
        ("dataset_num_proc", "dataset_num_proc"),
        ("pad_to_multiple_of", "pad_to_multiple_of"),
    ):
        _copy_if_present(request, config, source_key, target_key)

    return TRLTrainerRecipe(
        method="dpo",
        config_class="trl.DPOConfig",
        config_kwargs=config,
        runtime_args=deepcopy(getattr(recipe, "runtime_args", {}) or {}),
        environment=deepcopy(getattr(recipe, "environment", {}) or {}),
        provenance={"trl_version": trl_version, "source_recipe_schema": getattr(recipe, "schema_version", None)},
    )


def adapt_trl_grpo(recipe: Any, request: dict[str, Any], *, trl_version: str) -> TRLTrainerRecipe:
    _require_trl_113(recipe, trl_version)
    if str(getattr(recipe, "method", "")).lower() != "grpo":
        raise TRLAdapterError("GRPO adapter requires a GRPO compiled recipe")

    config = _base_config(recipe, request)
    runtime_args = deepcopy(getattr(recipe, "runtime_args", {}) or {})
    rollout = runtime_args.get("rollout_provider")
    if rollout == "vllm":
        config["use_vllm"] = True
        mode = request.get("grpo_vllm_mode")
        if mode is not None:
            if mode not in {"server", "colocate"}:
                raise TRLAdapterError("GRPO vLLM mode must be 'server' or 'colocate'")
            config["vllm_mode"] = mode
        if request.get("grpo_ds3_gather_for_generation") is False:
            raise TRLAdapterError("TRL 1.13 GRPO vLLM is incompatible with ds3_gather_for_generation=False")
    elif rollout in {None, "trl_inprocess"}:
        config["use_vllm"] = False
    else:
        raise TRLAdapterError(f"unsupported GRPO rollout provider: {rollout!r}")

    if request.get("grpo_generation_batch_size") is not None and request.get("grpo_steps_per_generation") is not None:
        raise TRLAdapterError("generation_batch_size and steps_per_generation are mutually exclusive")

    for source_key, target_key in (
        ("grpo_num_generations", "num_generations"),
        ("grpo_num_generations_eval", "num_generations_eval"),
        ("grpo_max_completion_length", "max_completion_length"),
        ("grpo_generation_batch_size", "generation_batch_size"),
        ("grpo_steps_per_generation", "steps_per_generation"),
        ("grpo_temperature", "temperature"),
        ("grpo_top_p", "top_p"),
        ("grpo_top_k", "top_k"),
        ("grpo_min_p", "min_p"),
        ("grpo_generation_kwargs", "generation_kwargs"),
        ("grpo_repetition_penalty", "repetition_penalty"),
        ("grpo_beta", "beta"),
        ("grpo_num_iterations", "num_iterations"),
        ("grpo_epsilon", "epsilon"),
        ("grpo_epsilon_high", "epsilon_high"),
        ("grpo_loss_type", "loss_type"),
        ("grpo_reward_weights", "reward_weights"),
        ("grpo_scale_rewards", "scale_rewards"),
        ("grpo_multi_objective_aggregation", "multi_objective_aggregation"),
        ("grpo_ds3_gather_for_generation", "ds3_gather_for_generation"),
        ("grpo_vllm_model_impl", "vllm_model_impl"),
        ("grpo_vllm_enable_sleep_mode", "vllm_enable_sleep_mode"),
        ("grpo_vllm_server_base_url", "vllm_server_base_url"),
        ("grpo_vllm_server_host", "vllm_server_host"),
        ("grpo_vllm_server_port", "vllm_server_port"),
        ("grpo_vllm_server_timeout", "vllm_server_timeout"),
        ("grpo_vllm_gpu_memory_utilization", "vllm_gpu_memory_utilization"),
        ("grpo_vllm_max_model_length", "vllm_max_model_length"),
        ("grpo_vllm_tensor_parallel_size", "vllm_tensor_parallel_size"),
    ):
        _copy_if_present(request, config, source_key, target_key)

    return TRLTrainerRecipe(
        method="grpo",
        config_class="trl.GRPOConfig",
        config_kwargs=config,
        runtime_args=runtime_args,
        environment=deepcopy(getattr(recipe, "environment", {}) or {}),
        provenance={"trl_version": trl_version, "source_recipe_schema": getattr(recipe, "schema_version", None)},
    )


def adapt_trl_distillation(recipe: Any, request: dict[str, Any], *, trl_version: str) -> TRLTrainerRecipe:
    _require_trl_113(recipe, trl_version)
    if str(getattr(recipe, "method", "")).lower() != "distillation":
        raise TRLAdapterError("distillation adapter requires a distillation compiled recipe")

    runtime_args = deepcopy(getattr(recipe, "runtime_args", {}) or {})
    teacher_provider = runtime_args.get("teacher_provider")
    if teacher_provider == "vllm":
        raise TRLAdapterError(
            "TRL 1.13 DistillationConfig has no remote-teacher provider field; a governed TeacherProvider adapter is required"
        )

    teacher_model = request.get("teacher_model_name_or_path")
    if not teacher_model:
        raise TRLAdapterError("local TRL distillation requires teacher_model_name_or_path")

    config = _base_config(recipe, request)
    config["teacher_model_name_or_path"] = str(teacher_model)
    for source_key, target_key in (
        ("teacher_model_revision", "teacher_model_revision"),
        ("teacher_model_init_kwargs", "teacher_model_init_kwargs"),
        ("distillation_max_completion_length", "max_completion_length"),
        ("distillation_temperature", "temperature"),
        ("distillation_top_p", "top_p"),
        ("distillation_top_k", "top_k"),
        ("distillation_min_p", "min_p"),
        ("distillation_generation_kwargs", "generation_kwargs"),
        ("distillation_repetition_penalty", "repetition_penalty"),
        ("distillation_beta", "beta"),
        ("distillation_max_tool_calling_iterations", "max_tool_calling_iterations"),
        ("distillation_shuffle_dataset", "shuffle_dataset"),
        ("pad_to_multiple_of", "pad_to_multiple_of"),
    ):
        _copy_if_present(request, config, source_key, target_key)

    beta = config.get("beta")
    if beta is not None and not 0.0 <= float(beta) <= 1.0:
        raise TRLAdapterError("TRL 1.13 DistillationConfig beta must be in [0.0, 1.0]")

    sequence_parallelism = runtime_args.get("sequence_parallelism")
    if sequence_parallelism in {"cp", "sp"}:
        raise TRLAdapterError("TRL 1.13 DistillationTrainer does not support CP/SP sequence-dimension parallelism")

    return TRLTrainerRecipe(
        method="distillation",
        config_class="trl.DistillationConfig",
        config_kwargs=config,
        runtime_args=runtime_args,
        environment=deepcopy(getattr(recipe, "environment", {}) or {}),
        provenance={"trl_version": trl_version, "source_recipe_schema": getattr(recipe, "schema_version", None)},
    )
