from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from .teacher_provider import TeacherProviderPlan, TeacherProviderStatus


class RemoteBridgeStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    FALLBACK = "FALLBACK"
    NEEDS_CANARY = "NEEDS_CANARY"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class TeacherLogitsTransportProfile:
    protocol: str
    streaming_full_vocab_logits: bool | None = None
    bounded_chunk_tokens: int | None = None
    accepts_attention_mask: bool | None = None
    completion_alignment_verified: bool | None = None
    numeric_equivalence_canary: bool | None = None
    binary_or_tensor_transport: bool | None = None

    def __post_init__(self) -> None:
        if not self.protocol.strip():
            raise ValueError("protocol is required")
        if self.bounded_chunk_tokens is not None and self.bounded_chunk_tokens <= 0:
            raise ValueError("bounded_chunk_tokens must be positive")


@dataclass(frozen=True)
class RemoteDistillationBridgePlan:
    status: RemoteBridgeStatus
    hook: str = "_compute_loss"
    strategy: str = "remote_full_vocab_logits"
    chunk_tokens: int | None = None
    rules: tuple[str, ...] = field(default_factory=tuple)
    canaries: tuple[str, ...] = field(default_factory=tuple)
    evidence: tuple[str, ...] = field(default_factory=tuple)
    fallback_teacher_model: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def allow_continue(self) -> bool:
        return self.status in {RemoteBridgeStatus.SUPPORTED, RemoteBridgeStatus.FALLBACK}

    def to_json(self) -> str:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["allow_continue"] = self.allow_continue
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def estimate_logits_chunk_bytes(vocab_size: int, chunk_tokens: int, dtype_bytes: int = 2) -> int:
    if vocab_size <= 0 or chunk_tokens <= 0 or dtype_bytes <= 0:
        raise ValueError("positive dimensions are required")
    return vocab_size * chunk_tokens * dtype_bytes


def plan_remote_distillation_bridge(
    recipe: Any,
    teacher_plan: TeacherProviderPlan,
    transport: TeacherLogitsTransportProfile,
    *,
    trl_version: str,
    student_is_vlm: bool = False,
    max_chunk_bytes: int = 128 * 1024 * 1024,
    vocab_size: int | None = None,
) -> RemoteDistillationBridgePlan:
    if trl_version != "1.13.0":
        return RemoteDistillationBridgePlan(
            RemoteBridgeStatus.UNSUPPORTED,
            rules=("bridge.trl.exact_113_required",),
        )

    if (
        str(getattr(recipe, "method", "")).lower() != "distillation"
        or getattr(recipe, "training_engine", None) != "trl"
    ):
        return RemoteDistillationBridgePlan(
            RemoteBridgeStatus.UNSUPPORTED,
            rules=("bridge.distillation_recipe.required",),
        )

    if not getattr(recipe, "executable", False):
        return RemoteDistillationBridgePlan(
            RemoteBridgeStatus.UNSUPPORTED,
            rules=("bridge.recipe.executable_required",),
        )

    if teacher_plan.status is TeacherProviderStatus.FALLBACK:
        return RemoteDistillationBridgePlan(
            RemoteBridgeStatus.FALLBACK,
            strategy="local_teacher_fallback",
            rules=teacher_plan.rules,
            evidence=teacher_plan.evidence,
            fallback_teacher_model=teacher_plan.fallback_teacher_model,
        )

    if teacher_plan.status is TeacherProviderStatus.UNSUPPORTED:
        return RemoteDistillationBridgePlan(
            RemoteBridgeStatus.UNSUPPORTED,
            rules=teacher_plan.rules or ("bridge.teacher.unsupported",),
            evidence=teacher_plan.evidence,
        )

    if teacher_plan.status is TeacherProviderStatus.NEEDS_CANARY:
        return RemoteDistillationBridgePlan(
            RemoteBridgeStatus.NEEDS_CANARY,
            canaries=teacher_plan.canaries or ("teacher_provider",),
            evidence=teacher_plan.evidence,
        )

    if teacher_plan.endpoint is None:
        return RemoteDistillationBridgePlan(
            RemoteBridgeStatus.UNSUPPORTED,
            rules=("bridge.teacher.endpoint_required",),
        )

    # The current protocol carries token IDs only. Multimodal distillation also needs the
    # exact image/video tensors or equivalent remote preprocessing contract, so do not
    # silently drop them.
    if student_is_vlm:
        return RemoteDistillationBridgePlan(
            RemoteBridgeStatus.UNSUPPORTED,
            rules=("bridge.remote_vlm.protocol_not_supported",),
        )

    if transport.protocol != teacher_plan.endpoint.protocol:
        return RemoteDistillationBridgePlan(
            RemoteBridgeStatus.UNSUPPORTED,
            rules=("bridge.teacher.protocol_mismatch",),
        )

    missing: list[str] = []
    for name, value in (
        ("teacher_streaming_full_vocab_logits", transport.streaming_full_vocab_logits),
        ("teacher_attention_mask_contract", transport.accepts_attention_mask),
        ("teacher_completion_alignment", transport.completion_alignment_verified),
        ("teacher_numeric_equivalence", transport.numeric_equivalence_canary),
        ("teacher_binary_tensor_transport", transport.binary_or_tensor_transport),
    ):
        if value is False:
            return RemoteDistillationBridgePlan(
                RemoteBridgeStatus.UNSUPPORTED,
                rules=(f"bridge.{name}.required",),
            )
        if value is None:
            missing.append(name)

    if transport.bounded_chunk_tokens is None:
        missing.append("teacher_bounded_chunk_transport")

    if missing:
        return RemoteDistillationBridgePlan(
            RemoteBridgeStatus.NEEDS_CANARY,
            canaries=tuple(missing),
            evidence=teacher_plan.evidence,
        )

    if vocab_size is not None:
        estimated_chunk_bytes = estimate_logits_chunk_bytes(vocab_size, transport.bounded_chunk_tokens)
        if estimated_chunk_bytes > max_chunk_bytes:
            return RemoteDistillationBridgePlan(
                RemoteBridgeStatus.NEEDS_CANARY,
                canaries=("teacher_logits_chunk_memory_budget",),
                evidence=teacher_plan.evidence,
                provenance={
                    "estimated_chunk_bytes": estimated_chunk_bytes,
                    "max_chunk_bytes": max_chunk_bytes,
                },
            )

    return RemoteDistillationBridgePlan(
        RemoteBridgeStatus.SUPPORTED,
        chunk_tokens=transport.bounded_chunk_tokens,
        evidence=teacher_plan.evidence,
        provenance={
            "trl_version": trl_version,
            "upstream_hook": "DistillationTrainer._compute_loss",
            "transport_protocol": transport.protocol,
        },
    )
