from __future__ import annotations

from copy import deepcopy
from typing import Any

from .hardware_doctor_contract import CapabilityState, PlannerCapabilityInput


class CapabilityInputConflict(ValueError):
    """Raised when measured capability input contradicts an explicit factual identity."""


def _set_fact(mapping: dict[str, Any], key: str, value: Any, path: str) -> None:
    if key in mapping and mapping[key] != value:
        raise CapabilityInputConflict(
            f"capability fact conflict at {path}: request={mapping[key]!r} evidence={value!r}"
        )
    mapping[key] = value


def _set_default(mapping: dict[str, Any], key: str, value: Any) -> None:
    if key not in mapping:
        mapping[key] = value


def _package_versions(capability_input: PlannerCapabilityInput) -> dict[str, str]:
    return {item.name: item.version for item in capability_input.runtime.packages}


def _map_packages(request: dict[str, Any], capability_input: PlannerCapabilityInput) -> None:
    observed = _package_versions(capability_input)
    packages = dict(request.get("packages", {}))
    for name, version in observed.items():
        _set_fact(packages, name, version, f"packages.{name}")
    if packages:
        request["packages"] = packages

    aliases = {
        "accelerate": "accelerate",
        "transformers": "transformers_version",
        "trl": "trl_version",
        "deepspeed": "deepspeed",
    }
    for package_name, request_key in aliases.items():
        if package_name in observed:
            _set_fact(request, request_key, observed[package_name], request_key)


def _map_hardware(request: dict[str, Any], capability_input: PlannerCapabilityInput) -> None:
    snapshot = capability_input.hardware
    hardware = dict(request.get("hardware", {}))
    _set_fact(hardware, "gpu", bool(snapshot.gpus), "hardware.gpu")
    _set_fact(hardware, "gpu_count", len(snapshot.gpus), "hardware.gpu_count")
    _set_fact(
        hardware,
        "vram_bytes",
        [device.vram_bytes for device in snapshot.gpus],
        "hardware.vram_bytes",
    )
    _set_fact(hardware, "ram_bytes", snapshot.ram_bytes, "hardware.ram_bytes")
    request["hardware"] = hardware


def _map_model(request: dict[str, Any], capability_input: PlannerCapabilityInput) -> None:
    model = capability_input.model
    resolved = model.resolved_capabilities()
    factual_mappings = {
        "max_context": "native_context_tokens",
        "kv_heads": "kv_heads",
        "supports_context_parallel": "model_supports_context_parallel",
        "causal_attention": "causal_attention",
    }
    for capability_name, request_key in factual_mappings.items():
        if capability_name in resolved:
            _set_fact(request, request_key, resolved[capability_name], request_key)

    request["capability_model"] = {
        "model_id": model.model_id,
        "family": model.family,
        "evidence": list(model.evidence),
    }


def _usable_state(state: CapabilityState) -> bool:
    return state in {CapabilityState.PROBED, CapabilityState.CANARY}


def _map_runtime_capabilities(request: dict[str, Any], capability_input: PlannerCapabilityInput) -> None:
    runtime = capability_input.runtime

    liger = runtime.capability_state("kernel.liger")
    if _usable_state(liger):
        _set_default(request, "liger_available", True)
        if liger is CapabilityState.CANARY:
            _set_default(request, "liger_canary_passed", True)
    elif liger is CapabilityState.UNSUPPORTED:
        _set_default(request, "liger_available", False)

    fastpath = runtime.capability_state("kernel.liger.preference_frozen_weight_fastpath")
    if _usable_state(fastpath):
        _set_default(request, "liger_preference_frozen_weight_fastpath", True)

    fsdp2 = runtime.capability_state("distributed.fsdp2")
    if _usable_state(fsdp2):
        _set_default(request, "fsdp2_available", True)

    attention_candidates: list[str] = []
    for backend in ("sdpa", "flash_attention_4", "flash_attention_torch"):
        state = runtime.capability_state(f"attention.{backend}")
        if _usable_state(state):
            attention_candidates.append(backend)
    if "attention" not in request and len(attention_candidates) == 1:
        request["attention"] = attention_candidates[0]

    request["capability_runtime"] = {
        "provider_id": runtime.provider_id,
        "isolation": runtime.isolation,
        "requires_isolation": runtime.requires_isolation,
        "conflicts": list(runtime.conflicts),
        "license_boundary": runtime.license_boundary,
    }


def _map_memory(request: dict[str, Any], capability_input: PlannerCapabilityInput) -> None:
    estimate = capability_input.memory
    if estimate is None:
        return
    request["memory_estimate"] = {
        "bytes_required": estimate.bytes_required,
        "basis": estimate.basis,
        "confidence": estimate.confidence,
        "assumptions": list(estimate.assumptions),
        "evidence": estimate.evidence,
    }


def adapt_training_request(
    request: dict[str, Any],
    capability_input: PlannerCapabilityInput,
) -> dict[str, Any]:
    """Return a capability-enriched copy without mutating or silently rewriting input."""
    adapted = deepcopy(request)
    _map_packages(adapted, capability_input)
    _map_hardware(adapted, capability_input)
    _map_model(adapted, capability_input)
    _map_runtime_capabilities(adapted, capability_input)
    _map_memory(adapted, capability_input)
    adapted["capability_schema_version"] = capability_input.schema_version
    adapted["capability_evidence"] = list(capability_input.evidence)
    return adapted
