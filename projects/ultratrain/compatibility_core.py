from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Decision(str, Enum):
    SUPPORTED = "SUPPORTED"
    FALLBACK = "FALLBACK"
    NEEDS_CANARY = "NEEDS_CANARY"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class CompatibilityResult:
    profile_id: str | None
    status: Decision
    rules: tuple[str, ...] = field(default_factory=tuple)
    canaries: tuple[str, ...] = field(default_factory=tuple)

    @property
    def allow_continue(self) -> bool:
        return self.status in {Decision.SUPPORTED, Decision.FALLBACK}

    def to_json(self) -> str:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["allow_continue"] = self.allow_continue
        return json.dumps(payload, sort_keys=True)


def _result(profile: dict[str, Any], status: Decision, rule: str, canary: str | None = None) -> CompatibilityResult:
    canaries = (canary,) if canary else ()
    return CompatibilityResult(profile.get("profile_id"), status, (rule,), canaries)


def _version_tuple(value: str) -> tuple[int, int, int]:
    parts = value.split(".")
    if len(parts) < 3 or not all(part.isdigit() for part in parts[:3]):
        raise ValueError(value)
    return tuple(int(part) for part in parts[:3])


def _evaluate_tracking(profile: dict[str, Any]) -> CompatibilityResult | None:
    tracking = profile.get("tracking", {})
    if tracking.get("provider") != "mlflow":
        return None

    version = tracking.get("version")
    if not version:
        return _result(profile, Decision.NEEDS_CANARY, "tracking.mlflow.version_identity", "tracking_version_identity")
    try:
        vulnerable = _version_tuple(version) < (3, 15, 0)
    except ValueError:
        return _result(profile, Decision.NEEDS_CANARY, "tracking.mlflow.version_identity", "tracking_version_identity")

    exposed = tracking.get("network_exposure") in {"lan", "public"}
    if vulnerable and (tracking.get("webhooks_enabled") or exposed):
        return _result(profile, Decision.UNSUPPORTED, "tracking.mlflow.security_floor")
    if exposed and tracking.get("auth_mode", "none") == "none":
        return _result(profile, Decision.UNSUPPORTED, "tracking.auth.required_when_exposed")
    if tracking.get("network_exposure") == "public" and tracking.get("egress_policy", "open") == "open":
        return _result(profile, Decision.NEEDS_CANARY, "tracking.egress.isolation", "tracking_egress_isolation")
    return None


def evaluate_profile(profile: dict[str, Any]) -> CompatibilityResult:
    if not profile.get("profile_id"):
        return _result(profile, Decision.UNSUPPORTED, "profile_id.required")

    tracking_result = _evaluate_tracking(profile)
    if tracking_result is not None:
        return tracking_result

    trl = profile.get("trl", {})
    distributed = profile.get("distributed", {})
    runtime = profile.get("runtime", {})
    packages = profile.get("packages", {})
    trl_version = trl.get("version")
    parsed_trl_version = None
    if trl_version:
        try:
            parsed_trl_version = _version_tuple(trl_version)
        except ValueError:
            return _result(profile, Decision.NEEDS_CANARY, "trl.version_identity", "trl_version_identity")

    if trl.get("packing") and distributed.get("context_parallelism"):
        return _result(profile, Decision.UNSUPPORTED, "trl.packing_context_parallelism.incompatible")

    if trl.get("async_distillation"):
        if not runtime.get("vllm"):
            return _result(profile, Decision.UNSUPPORTED, "trl.async_distillation.requires_vllm")
        transformers_version = packages.get("transformers")
        try:
            transformers_ok = transformers_version is not None and _version_tuple(transformers_version) >= (5, 2, 0)
        except ValueError:
            transformers_ok = False
        if not transformers_ok:
            return _result(profile, Decision.UNSUPPORTED, "trl.async_distillation.requires_transformers_52")
        if distributed.get("enabled") and distributed.get("fsdp_version") != 2:
            return _result(profile, Decision.UNSUPPORTED, "trl.async_distillation.distributed_requires_fsdp2")

    if trl.get("vllm_server_mode") and parsed_trl_version in {(1, 11, 0), (1, 12, 0)}:
        vllm_version = runtime.get("vllm_version")
        try:
            vllm_post_security_floor = vllm_version is not None and _version_tuple(vllm_version) >= (0, 28, 0)
        except ValueError:
            vllm_post_security_floor = False
        if vllm_post_security_floor and not trl.get("vllm_028_canary_passed"):
            return _result(profile, Decision.NEEDS_CANARY, "trl.vllm_server.post_027_compatibility", "trl_vllm_server_compatibility")

    transformers = profile.get("transformers", {})
    if transformers.get("untrusted_repo"):
        if not transformers.get("sandboxed"):
            return _result(profile, Decision.UNSUPPORTED, "transformers.untrusted_repo.sandbox")
        if not transformers.get("revision_pinned"):
            return _result(profile, Decision.UNSUPPORTED, "transformers.untrusted_repo.revision_pin")

    peft = profile.get("peft", {})
    hardware = profile.get("hardware", {})
    packages = profile.get("packages", {})
    if peft.get("qlora_4bit") and not hardware.get("gpu"):
        return _result(profile, Decision.UNSUPPORTED, "qlora_4bit.requires_gpu")
    if peft.get("qlora_4bit") and not packages.get("bitsandbytes"):
        return _result(profile, Decision.UNSUPPORTED, "qlora_4bit.requires_bitsandbytes")

    distributed = profile.get("distributed", {})
    if "nodes" in distributed and distributed["nodes"] <= 0:
        return _result(profile, Decision.UNSUPPORTED, "distributed.nodes.positive")
    if distributed.get("fsdp_version") == 2 and peft.get("qlora_4bit"):
        accelerate_version = packages.get("accelerate")
        try:
            accelerate_hardened = accelerate_version is not None and _version_tuple(accelerate_version) >= (1, 14, 0)
        except ValueError:
            accelerate_hardened = False
        if not accelerate_hardened:
            return _result(profile, Decision.NEEDS_CANARY, "distributed.fsdp2_qlora.hardening", "fsdp2_qlora_compatibility")

    megatron = profile.get("megatron", {})
    if megatron.get("enabled") and megatron.get("multi_grid") and not megatron.get("explicit_process_groups"):
        return _result(profile, Decision.UNSUPPORTED, "megatron.multigrid.explicit_process_groups")

    ray = profile.get("ray", {})
    if ray.get("requested") and not ray.get("enabled"):
        return _result(profile, Decision.UNSUPPORTED, "ray.explicit_enablement")

    dataset = profile.get("dataset", {})
    if dataset.get("schema_valid") is False:
        return _result(profile, Decision.UNSUPPORTED, "dataset.schema_valid")

    export = profile.get("export", {})
    target = export.get("target")
    if target in {"gguf", "ollama"} and peft.get("lora") and not peft.get("merged"):
        return _result(profile, Decision.UNSUPPORTED, "export.requires_merged_lora")
    if target == "gguf" and not export.get("converter_id"):
        return _result(profile, Decision.NEEDS_CANARY, "gguf.converter_identity", "gguf_converter_identity")

    hub = profile.get("hub", {})
    if hub.get("xet") and not hub.get("xet_canary_passed"):
        return _result(profile, Decision.NEEDS_CANARY, "hub.xet.canary", "xet_roundtrip")

    runtime = profile.get("runtime", {})
    if runtime.get("sglang") and runtime.get("sglang_gptq_marlin_moe"):
        if runtime.get("dtype") in {"bfloat16", "bf16"} and runtime.get("tensor_parallel_size", 1) > 1:
            if not runtime.get("sglang_gptq_marlin_moe_canary_passed"):
                return _result(profile, Decision.NEEDS_CANARY, "runtime.sglang.gptq_marlin_moe_bf16_tp", "sglang_gptq_marlin_moe_tp")

    if runtime.get("vllm"):
        vllm_version = runtime.get("vllm_version")
        parsed_vllm_version: tuple[int, int, int] | None = None
        if vllm_version:
            try:
                parsed_vllm_version = _version_tuple(vllm_version)
                if parsed_vllm_version < (0, 28, 0):
                    return _result(profile, Decision.UNSUPPORTED, "runtime.vllm.security_floor_028")
            except ValueError:
                return _result(profile, Decision.NEEDS_CANARY, "runtime.vllm.version_identity", "vllm_version_identity")

        if parsed_vllm_version == (0, 27, 1):
            if peft.get("lora") and runtime.get("vllm_sleep_level") == 1:
                if not runtime.get("post_wake_determinism_canary_passed"):
                    return _result(profile, Decision.NEEDS_CANARY, "runtime.vllm.lora_sleep_wake_integrity", "vllm_lora_sleep_wake")
            if runtime.get("vllm_tool_server"):
                mcp_version = packages.get("mcp")
                if mcp_version:
                    try:
                        if _version_tuple(mcp_version) >= (2, 0, 0):
                            return _result(profile, Decision.UNSUPPORTED, "runtime.vllm.mcp2_incompatible")
                    except ValueError:
                        return _result(profile, Decision.NEEDS_CANARY, "runtime.vllm.mcp_version_identity", "vllm_mcp_compatibility")

        if not runtime.get("vllm_canary_passed"):
            return _result(profile, Decision.NEEDS_CANARY, "runtime.vllm.canary", "vllm_runtime")

    return _result(profile, Decision.SUPPORTED, "baseline.supported")
