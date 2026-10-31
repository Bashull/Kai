"""UltraTrain 2026-10-31 advisory gates — STAGING, never authorization.

Source releases:
https://github.com/huggingface/transformers/releases/tag/v5.22.0
https://github.com/pytorch/torchtitan/releases/tag/v0.4.0
This is a focused GitHub candidate; the local donor ZIP contains the full
inherited composition and 550 synthetic tests. Profiles are untrusted claims.
"""
from __future__ import annotations
import re
from typing import Any

_VERSION = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$", re.ASCII)
_PRIORITY = {"UNSUPPORTED": 2, "NEEDS_CANARY": 1}


def _v(value: Any) -> tuple[int, int, int] | None:
    match = _VERSION.fullmatch(value.strip()) if isinstance(value, str) else None
    return tuple(map(int, match.groups())) if match else None


def assess_20261031(profile: Any) -> dict[str, Any]:
    sections = ("packages", "training", "quantization", "distributed", "torchtitan",
                "pipeline", "data", "checkpoint", "rl", "hardware", "model")
    if not isinstance(profile, dict) or any(not isinstance(profile.get(s, {}), dict) for s in sections):
        return {"status": "NEEDS_CANARY", "allow_continue": False,
                "findings": [{"status": "NEEDS_CANARY", "rule": "release1031.profile_shape",
                              "canary": "profile_schema"}]}

    packages = profile.get("packages", {})
    training = profile.get("training", {})
    quant = profile.get("quantization", {})
    dist = profile.get("distributed", {})
    titan = profile.get("torchtitan", {})
    pipeline = profile.get("pipeline", {})
    data = profile.get("data", {})
    checkpoint = profile.get("checkpoint", {})
    rl = profile.get("rl", {})
    hardware = profile.get("hardware", {})
    model = profile.get("model", {})
    out: list[dict[str, str]] = []

    def add(status: str, rule: str, canary: str) -> None:
        out.append({"status": status, "rule": rule, "canary": canary})

    tf = _v(packages.get("transformers"))
    if tf is not None and tf >= (5, 22, 0):
        if training.get("adapter_training") is True and quant.get("base_weight_format") == "fp8":
            backend = quant.get("expert_matmul_backend")
            if backend in ("deepgemm", "batched_mm"):
                add("UNSUPPORTED", "tf522.fp8_backward_unimplemented_backend", "eager_or_grouped_mm_fallback")
            elif backend not in ("eager", "grouped_mm"):
                add("NEEDS_CANARY", "tf522.fp8_backend_unknown", "kernel_dispatch_provenance")
            if quant.get("gradient_parity_canary") is not True:
                add("NEEDS_CANARY", "tf522.fp8_gradient_parity", "input_adapter_gradients_vs_bf16_fp32")
            if quant.get("memory_canary") is not True:
                add("NEEDS_CANARY", "tf522.fp8_memory", "measured_peak_latency_and_oom")
            if training.get("merge_reload_canary") is not True:
                add("NEEDS_CANARY", "tf522.fp8_adapter_merge", "merge_reload_task_eval_parity")
        if training.get("adapter_training") is True and quant.get("base_weight_format") == "fp4" and quant.get("needs_input_backward") is True:
            add("UNSUPPORTED", "tf522.fp4_backward_not_supported", "bf16_or_supported_fp8_fallback")
        if dist.get("custom_ep_extensions") is True:
            if dist.get("old_ep_base_class") is True or dist.get("private_tp_helpers") is True:
                add("UNSUPPORTED", "tf522.ep_extension_migration", "ExpertParallelLayer_parallel_utils")
            if dist.get("old_ep_import") is True:
                add("NEEDS_CANARY", "tf522.ep_import_deprecation", "expert_parallel_import_before_523")
        if pipeline.get("uses_remote_code") is True:
            if not pipeline.get("code_revision"):
                add("NEEDS_CANARY", "tf522.remote_code_unpinned", "model_tokenizer_processor_commit")
            elif pipeline.get("revision_parity_canary") is not True:
                add("NEEDS_CANARY", "tf522.pipeline_revision_parity", "all_loader_code_revision_receipts")
            if pipeline.get("code_revision_both_locations") is True:
                add("UNSUPPORTED", "tf522.duplicate_code_revision", "single_argument_location")
        if data.get("numpy_integer_labels") is True and data.get("dtype_parity_canary") is not True:
            add("NEEDS_CANARY", "tf522.numpy_label_dtype", "collator_dtype_loss_parity")
        if model.get("family") == "mistral_large_4":
            if model.get("license_reviewed") is not True:
                add("NEEDS_CANARY", "tf522.mistral4_license", "license_and_use_case")
            if model.get("business_model") == "model_as_a_service" and model.get("maas_separate_license") is not True:
                add("UNSUPPORTED", "tf522.mistral4_maas_license", "commercial_permission")

    tv = _v(packages.get("torchtitan") or titan.get("version"))
    if tv is not None and tv >= (0, 4, 0) and (titan.get("enabled") is True or training.get("backend") == "torchtitan"):
        torch = _v(packages.get("torch"))
        if torch is None or torch < (2, 15, 0):
            # Release aligns with 2.15; tagged requirements do NOT hard-pin torch.
            add("NEEDS_CANARY", "titan040.torch_alignment", "resolver_and_gpu_compatibility")
        if training.get("whole_block_compile") is True or dist.get("ep_backend") in ("MinimalAsyncEP", "full_dtensor"):
            add("UNSUPPORTED", "titan040.removed_legacy_path", "local_compile_regions_supported_spmd")
        if training.get("mxfp8") is True and titan.get("torchao_nightly_verified") is not True:
            add("UNSUPPORTED", "titan040.mxfp8_torchao_nightly", "exact_nightly_kernel_build")
        if data.get("grain_pipeline") is True and data.get("iterator_resume_canary") is not True:
            add("NEEDS_CANARY", "titan040.grain_resume", "cursor_rng_mix_pack_prefetch")
        if checkpoint.get("hf_dcp") is True and checkpoint.get("resume_canary") is not True:
            add("NEEDS_CANARY", "titan040.dcp_resume", "rank_shards_ema_bf16_optimizer")
        if training.get("sdc_replay") is True:
            if training.get("deterministic_execution") is not True:
                add("UNSUPPORTED", "titan040.sdc_requires_determinism", "deterministic_replay")
            elif training.get("sdc_replay_canary") is not True:
                add("NEEDS_CANARY", "titan040.sdc_replay", "fwd_bwd_pipeline_microbatch")
        if rl.get("titanrl") is True:
            if rl.get("import_path") == "torchtitan.experiments.rl":
                add("UNSUPPORTED", "titan040.titanrl_import_moved", "torchtitan_rl_shared_engine")
            if rl.get("multiturn_kv_reuse") is True and rl.get("session_isolation_canary") is not True:
                add("NEEDS_CANARY", "titan040.session_kv_isolation", "multi_tenant_abort_replay")
    out.sort(key=lambda x: (-_PRIORITY[x["status"]], x["rule"]))
    return {"status": out[0]["status"] if out else "NO_NEW_GATE",
            "allow_continue": False, "findings": out}
