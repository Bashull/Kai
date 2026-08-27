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
    if runtime.get("vllm") and not runtime.get("vllm_canary_passed"):
        return _result(profile, Decision.NEEDS_CANARY, "runtime.vllm.canary", "vllm_runtime")

    return _result(profile, Decision.SUPPORTED, "baseline.supported")
