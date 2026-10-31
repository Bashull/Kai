"""2026-10-30 UltraTrain STAGING: RL logprob/retraction/profiling/PDL gates.

Advisory only; input profiles are claims, not runtime attestation.
Never authorizes execution, promotion or deployment.
Sources:
https://github.com/NVIDIA/Megatron-LM/pull/8248
https://github.com/sgl-project/sglang/issues/47245
https://github.com/sgl-project/sglang/issues/47294
https://github.com/vllm-project/vllm/pull/64420
"""
from __future__ import annotations
import re
from typing import Any

_VERSION = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$", re.ASCII)
_ORDER = {"UNSUPPORTED": 2, "NEEDS_CANARY": 1}

def _version(raw: Any) -> tuple[int, int, int] | None:
    m = _VERSION.fullmatch(raw.strip()) if isinstance(raw, str) else None
    return tuple(int(m.group(i)) for i in (1, 2, 3)) if m else None

def findings_release_20261030(profile: Any) -> list[dict[str, str]]:
    if not isinstance(profile, dict) or any(
        not isinstance(profile.get(k, {}), dict)
        for k in ("packages", "training", "rl", "runtime", "sampling", "profiling")
    ):
        return [{"status": "NEEDS_CANARY", "rule": "release1030.profile_shape", "canary": "profile_schema"}]
    packages = profile.get("packages", {})
    training = profile.get("training", {})
    rl = profile.get("rl", {})
    runtime = profile.get("runtime", {})
    sampling = profile.get("sampling", {})
    profiling = profile.get("profiling", {})
    out: list[dict[str, str]] = []

    def add(status: str, rule: str, canary: str) -> None:
        out.append({"status": status, "rule": rule, "canary": canary})

    megatron = (training.get("backend") in ("megatron", "megatron_core")
                or rl.get("backend") in ("megatron", "megatron_core"))
    if megatron and rl.get("vocab_parallel_logprobs") is True:
        tp = training.get("tensor_parallel_size", rl.get("tensor_parallel_size"))
        if type(tp) is not int or tp < 1:
            add("NEEDS_CANARY", "megatron.rl.tp_world_unknown", "runtime_tp_world_and_rank_identity")
        if rl.get("batch_invariant_mode") is True:
            if rl.get("reduction_algorithm") == "nccl_sum_order":
                add("UNSUPPORTED", "megatron.rl.batch_variant_reduction", "permutation_and_batch_size_bitwise_logprob_parity")
            if rl.get("merged_pr_8248_present") is not True:
                add("NEEDS_CANARY", "megatron.rl.merged_fix_provenance", "installed_commit_sha_and_code_path")
            if rl.get("fp32_output_verified") is not True:
                add("NEEDS_CANARY", "megatron.rl.fp32_logprobs_contract", "output_dtype_and_gradient_parity")
            if rl.get("bitwise_batch_permutation_canary") is not True:
                add("NEEDS_CANARY", "megatron.rl.batch_invariant_canary", "same_sample_alone_reordered_mixed_batch_tp")
            if rl.get("backward_gradient_canary") is not True:
                add("NEEDS_CANARY", "megatron.rl.backward_parity", "tp_gradient_and_no_grad_consistency")
        if rl.get("trust_merely_merged_pr") is True:
            add("UNSUPPORTED", "megatron.rl.merged_not_runtime_attestation", "installed_commit_and_canary_receipts")

    sglang = runtime.get("provider") == "sglang" or runtime.get("sglang") is True
    if sglang:
        sv = _version(packages.get("sglang") or runtime.get("sglang_version"))
        if sv is None:
            add("NEEDS_CANARY", "sglang.1030.version_unknown", "package_container_digest_and_commit")
        penalties = any(sampling.get(k) not in (None, 0, 0.0, False) for k in
                        ("frequency_penalty", "presence_penalty"))
        repetition = sampling.get("repetition_penalty")
        if repetition is not None and repetition not in (1, 1.0, False):
            penalties = True
        min_tokens = sampling.get("min_new_tokens")
        if type(min_tokens) is int and min_tokens > 0:
            penalties = True
        if sampling.get("penalties_enabled") is True:
            penalties = True
        if penalties:
            if runtime.get("retraction_possible") is not False:
                if sv == (0, 5, 22) and runtime.get("retraction_history_patch_verified") is not True:
                    add("UNSUPPORTED", "sglang.1030.retraction_sampling_history_reset", "uninterrupted_vs_retracted_output_ids")
                else:
                    add("NEEDS_CANARY", "sglang.1030.retraction_penalty_parity", "frequency_presence_repetition_min_tokens_replay")
                if runtime.get("pd_disaggregation") is True:
                    add("NEEDS_CANARY", "sglang.1030.pd_prebuilt_retraction_gap", "decode_prebuilt_history_replay_and_abort")
            elif runtime.get("retraction_disabled_runtime_proof") is not True:
                add("NEEDS_CANARY", "sglang.1030.retraction_absence_unproven", "pressure_preemption_retract_path_trace")
        if profiling.get("endpoint_enabled") is True:
            if profiling.get("network_access") in ("public", "untrusted", "lan") and profiling.get("authenticated") is not True:
                add("UNSUPPORTED", "sglang.1030.profiling_endpoint_exposed", "authn_authz_admin_endpoint_restriction")
            if profiling.get("profile_by_stage") is True:
                steps = profiling.get("num_steps")
                if type(steps) is not int or steps <= 0:
                    add("UNSUPPORTED", "sglang.1030.stage_profile_unbounded_crash", "invalid_stage_profile_rejected_before_scheduler")
                elif profiling.get("stage_profile_canary") is not True:
                    add("NEEDS_CANARY", "sglang.1030.stage_profile_scheduler_canary", "isolated_profile_start_stop_with_bounded_steps")
            if profiling.get("allow_user_supplied_output_dir") is True:
                add("NEEDS_CANARY", "sglang.1030.profile_output_path", "allowlisted_profile_destination_and_permissions")

    if runtime.get("provider") == "vllm" or runtime.get("vllm") is True:
        if (runtime.get("flashinfer_allreduce") is True
                and runtime.get("pdl_enabled") is True
                and runtime.get("small_oneshot_possible") is True):
            if runtime.get("completion_at_end_verified") is not True:
                add("NEEDS_CANARY", "vllm.1030.flashinfer_pdl_completion_race", "one_shot_auto_small_tokens_no_nan_no_uninitialized_read")
            if runtime.get("assume_pr_64420_shipped") is True:
                add("UNSUPPORTED", "vllm.1030.open_pr_not_release", "commit_and_container_digest_provenance")
    return sorted(out, key=lambda f: (-_ORDER[f["status"]], f["rule"]))
