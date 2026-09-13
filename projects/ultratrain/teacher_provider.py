from __future__ import annotations

import ipaddress
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
from urllib.parse import urlparse


class TeacherProviderStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    FALLBACK = "FALLBACK"
    NEEDS_CANARY = "NEEDS_CANARY"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class TeacherIdentity:
    model_id: str
    revision: str
    tokenizer_id: str
    vocab_size: int

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise ValueError("teacher model_id is required")
        if not self.revision.strip():
            raise ValueError("teacher revision is required")
        if not self.tokenizer_id.strip():
            raise ValueError("teacher tokenizer_id is required")
        if self.vocab_size <= 0:
            raise ValueError("teacher vocab_size must be positive")


@dataclass(frozen=True)
class TeacherEndpoint:
    provider_id: str
    base_url: str
    protocol: str = "ultratrain.teacher-logits/v1"
    auth_mode: str = "none"
    credential_ref: str | None = None
    timeout_seconds: float = 30.0
    max_retries: int = 2

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("teacher provider_id is required")
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("teacher base_url must be an absolute HTTP(S) URL")
        if parsed.scheme == "http" and not _is_loopback_host(parsed.hostname):
            raise ValueError("non-loopback remote teacher endpoints require HTTPS")
        if self.auth_mode not in {"none", "bearer_ref"}:
            raise ValueError("unsupported teacher auth_mode")
        if self.auth_mode == "bearer_ref" and not self.credential_ref:
            raise ValueError("bearer_ref auth requires credential_ref")
        if self.timeout_seconds <= 0:
            raise ValueError("teacher timeout_seconds must be positive")
        if self.max_retries < 0:
            raise ValueError("teacher max_retries cannot be negative")

    def to_safe_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TeacherCanaryEvidence:
    health_ok: bool | None = None
    identity_ok: bool | None = None
    tokenizer_compatible: bool | None = None
    vocab_compatible: bool | None = None
    full_vocab_logits: bool | None = None
    logits_contract_ok: bool | None = None
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TeacherProviderPlan:
    provider_kind: str
    status: TeacherProviderStatus
    identity: TeacherIdentity | None = None
    endpoint: TeacherEndpoint | None = None
    canaries: tuple[str, ...] = field(default_factory=tuple)
    rules: tuple[str, ...] = field(default_factory=tuple)
    evidence: tuple[str, ...] = field(default_factory=tuple)
    fallback_teacher_model: str | None = None

    @property
    def allow_continue(self) -> bool:
        return self.status in {TeacherProviderStatus.SUPPORTED, TeacherProviderStatus.FALLBACK}

    def to_json(self) -> str:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["allow_continue"] = self.allow_continue
        if self.endpoint is not None:
            payload["endpoint"] = self.endpoint.to_safe_dict()
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _is_loopback_host(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _unknown_canaries(evidence: TeacherCanaryEvidence) -> tuple[str, ...]:
    checks = (
        ("teacher_health", evidence.health_ok),
        ("teacher_identity", evidence.identity_ok),
        ("teacher_tokenizer_compatibility", evidence.tokenizer_compatible),
        ("teacher_vocab_compatibility", evidence.vocab_compatible),
        ("teacher_full_vocab_logits", evidence.full_vocab_logits),
        ("teacher_logits_contract", evidence.logits_contract_ok),
    )
    return tuple(name for name, value in checks if value is None)


def evaluate_remote_teacher(
    endpoint: TeacherEndpoint,
    identity: TeacherIdentity,
    evidence: TeacherCanaryEvidence,
    *,
    student_tokenizer_id: str,
    student_vocab_size: int,
    fallback_teacher_model: str | None = None,
) -> TeacherProviderPlan:
    if not student_tokenizer_id.strip() or student_vocab_size <= 0:
        raise ValueError("student tokenizer identity and vocab_size are required")

    hard_failures: list[str] = []
    if identity.tokenizer_id != student_tokenizer_id or evidence.tokenizer_compatible is False:
        hard_failures.append("teacher.tokenizer.incompatible")
    if identity.vocab_size != student_vocab_size or evidence.vocab_compatible is False:
        hard_failures.append("teacher.vocab.incompatible")
    if evidence.health_ok is False:
        hard_failures.append("teacher.health.failed")
    if evidence.identity_ok is False:
        hard_failures.append("teacher.identity.failed")
    if evidence.full_vocab_logits is False:
        hard_failures.append("teacher.full_vocab_logits.required")
    if evidence.logits_contract_ok is False:
        hard_failures.append("teacher.logits_contract.failed")

    if hard_failures:
        if fallback_teacher_model:
            return TeacherProviderPlan(
                provider_kind="local_fallback",
                status=TeacherProviderStatus.FALLBACK,
                identity=identity,
                endpoint=endpoint,
                rules=tuple(hard_failures),
                evidence=evidence.evidence_refs,
                fallback_teacher_model=fallback_teacher_model,
            )
        return TeacherProviderPlan(
            provider_kind="remote",
            status=TeacherProviderStatus.UNSUPPORTED,
            identity=identity,
            endpoint=endpoint,
            rules=tuple(hard_failures),
            evidence=evidence.evidence_refs,
        )

    canaries = _unknown_canaries(evidence)
    if canaries:
        return TeacherProviderPlan(
            provider_kind="remote",
            status=TeacherProviderStatus.NEEDS_CANARY,
            identity=identity,
            endpoint=endpoint,
            canaries=canaries,
            evidence=evidence.evidence_refs,
            fallback_teacher_model=fallback_teacher_model,
        )

    return TeacherProviderPlan(
        provider_kind="remote",
        status=TeacherProviderStatus.SUPPORTED,
        identity=identity,
        endpoint=endpoint,
        evidence=evidence.evidence_refs,
        fallback_teacher_model=fallback_teacher_model,
    )
