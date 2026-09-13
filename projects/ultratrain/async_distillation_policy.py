from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse


class AsyncDistillationStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    FALLBACK = "FALLBACK"
    NEEDS_CANARY = "NEEDS_CANARY"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class AsyncTeacherServer:
    teacher_id: str
    url: str
    tokenizer_id: str
    processed_logprobs: bool | None = None
    max_logprobs_unlimited: bool | None = None
    identity_canary_passed: bool | None = None

    def __post_init__(self) -> None:
        if not self.teacher_id.strip():
            raise ValueError("teacher_id is required")
        if not self.tokenizer_id.strip():
            raise ValueError("tokenizer_id is required")
        _validate_endpoint(self.url)


@dataclass(frozen=True)
class AsyncDistillationPlan:
    status: AsyncDistillationStatus
    trainer_class: str = "trl.experimental.async_distillation.AsyncDistillationTrainer"
    weight_delta_transport: str = "full_nccl"
    config_kwargs: dict = field(default_factory=dict)
    rules: tuple[str, ...] = field(default_factory=tuple)
    canaries: tuple[str, ...] = field(default_factory=tuple)
    decisions: tuple[str, ...] = field(default_factory=tuple)

    @property
    def allow_continue(self) -> bool:
        return self.status in {AsyncDistillationStatus.SUPPORTED, AsyncDistillationStatus.FALLBACK}


def _version_tuple(value: str | None) -> tuple[int, int, int] | None:
    if not value:
        return None
    parts = value.split(".")
    if len(parts) < 3 or not all(part.isdigit() for part in parts[:3]):
        return None
    return tuple(int(part) for part in parts[:3])


def _is_loopback(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _validate_endpoint(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("absolute HTTP(S) URL is required")
    if parsed.scheme == "http" and not _is_loopback(parsed.hostname):
        raise ValueError("non-loopback async distillation endpoints require HTTPS")


def plan_async_distillation(
    *,
    trl_version: str,
    vllm_version: str | None,
    student_server_url: str,
    student_tokenizer_id: str,
    teachers: tuple[AsyncTeacherServer, ...],
    teacher_top_k: int = 8,
    beta: float = 0.0,
    teacher_temperature: float = 1.0,
    add_tail_bucket: bool = True,
    student_server_dev_mode: bool | None = None,
    student_weight_transfer_backend: str | None = None,
    vllm_runtime_canary_passed: bool | None = None,
    requested_weight_delta: str | None = None,
    sequence_parallelism: str | None = None,
    request_timeout: int = 600,
    weight_sync_timeout: int = 1800,
) -> AsyncDistillationPlan:
    if trl_version != "1.13.0":
        return AsyncDistillationPlan(
            AsyncDistillationStatus.UNSUPPORTED,
            rules=("async_distillation.trl.exact_113_required",),
        )

    parsed_vllm = _version_tuple(vllm_version)
    if parsed_vllm is None:
        return AsyncDistillationPlan(
            AsyncDistillationStatus.NEEDS_CANARY,
            canaries=("async_distillation.vllm_version_identity",),
        )
    if parsed_vllm < (0, 28, 0):
        return AsyncDistillationPlan(
            AsyncDistillationStatus.UNSUPPORTED,
            rules=("async_distillation.vllm.security_floor_028",),
        )

    try:
        _validate_endpoint(student_server_url)
    except ValueError:
        return AsyncDistillationPlan(
            AsyncDistillationStatus.UNSUPPORTED,
            rules=("async_distillation.student_endpoint.security",),
        )

    if not student_tokenizer_id.strip():
        return AsyncDistillationPlan(
            AsyncDistillationStatus.UNSUPPORTED,
            rules=("async_distillation.student_tokenizer.required",),
        )
    if not teachers:
        return AsyncDistillationPlan(
            AsyncDistillationStatus.UNSUPPORTED,
            rules=("async_distillation.teacher_server.required",),
        )
    if not 0.0 <= beta <= 1.0:
        return AsyncDistillationPlan(
            AsyncDistillationStatus.UNSUPPORTED,
            rules=("async_distillation.beta.range",),
        )
    if teacher_temperature <= 0:
        return AsyncDistillationPlan(
            AsyncDistillationStatus.UNSUPPORTED,
            rules=("async_distillation.teacher_temperature.positive",),
        )
    if teacher_top_k <= 0:
        return AsyncDistillationPlan(
            AsyncDistillationStatus.UNSUPPORTED,
            rules=("async_distillation.teacher_top_k.positive",),
        )
    if sequence_parallelism in {"cp", "sp"}:
        return AsyncDistillationPlan(
            AsyncDistillationStatus.UNSUPPORTED,
            rules=("async_distillation.sequence_parallelism.unsupported",),
        )

    # TRL 1.13's async implementation owns a packed full-weight NCCL transfer to
    # the student's vLLM server. Advanced UltraTrain transports need a separate
    # adapter instead of being claimed by version identity alone.
    if requested_weight_delta not in {None, "full_nccl"}:
        return AsyncDistillationPlan(
            AsyncDistillationStatus.UNSUPPORTED,
            rules=("async_distillation.weight_delta.full_nccl_only",),
        )

    for teacher in teachers:
        if teacher.tokenizer_id != student_tokenizer_id:
            return AsyncDistillationPlan(
                AsyncDistillationStatus.UNSUPPORTED,
                rules=("async_distillation.teacher_tokenizer.mismatch",),
            )
        if teacher.processed_logprobs is False:
            return AsyncDistillationPlan(
                AsyncDistillationStatus.UNSUPPORTED,
                rules=("async_distillation.teacher.processed_logprobs.required",),
            )
        if teacher_top_k > 20 and teacher.max_logprobs_unlimited is False:
            return AsyncDistillationPlan(
                AsyncDistillationStatus.UNSUPPORTED,
                rules=("async_distillation.teacher.max_logprobs_unlimited.required",),
            )

    missing: list[str] = []
    if student_server_dev_mode is not True:
        missing.append("async_student_dev_mode")
    if student_weight_transfer_backend != "nccl":
        missing.append("async_student_nccl_weight_transfer")
    if vllm_runtime_canary_passed is not True:
        missing.append("async_vllm_runtime")

    for teacher in teachers:
        if teacher.processed_logprobs is not True:
            missing.append(f"teacher_{teacher.teacher_id}_processed_logprobs")
        if teacher.identity_canary_passed is not True:
            missing.append(f"teacher_{teacher.teacher_id}_identity")
        if teacher_top_k > 20 and teacher.max_logprobs_unlimited is not True:
            missing.append(f"teacher_{teacher.teacher_id}_max_logprobs_unlimited")

    config_kwargs = {
        "vllm_server_base_url": student_server_url,
        "teacher_server_urls": {teacher.teacher_id: teacher.url for teacher in teachers},
        "teacher_top_k": teacher_top_k,
        "beta": beta,
        "teacher_temperature": teacher_temperature,
        "add_tail_bucket": add_tail_bucket,
        "request_timeout": request_timeout,
        "weight_sync_timeout": weight_sync_timeout,
    }
    decisions = (
        "async_distillation.upstream_selected",
        "async_distillation.weight_delta.full_nccl",
    )

    if missing:
        return AsyncDistillationPlan(
            AsyncDistillationStatus.NEEDS_CANARY,
            config_kwargs=config_kwargs,
            canaries=tuple(dict.fromkeys(missing)),
            decisions=decisions,
        )

    return AsyncDistillationPlan(
        AsyncDistillationStatus.SUPPORTED,
        config_kwargs=config_kwargs,
        decisions=decisions + ("async_distillation.teacher_sparse_topk",),
    )
