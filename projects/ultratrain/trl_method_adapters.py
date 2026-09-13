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
