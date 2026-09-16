"""Evidence contract and stable hashing helpers for Loop Factory."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from .model import ErrorClass, JobState


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(slots=True)
class EvidenceRecord:
    run_id: str
    job_id: str
    parent_run_id: str | None
    timestamp_start: str
    timestamp_end: str
    host: str
    worker: str
    model_or_provider: str | None
    tool: str
    input_hashes: Mapping[str, str] = field(default_factory=dict)
    output_hashes: Mapping[str, str] = field(default_factory=dict)
    branch: str | None = None
    commit_sha: str | None = None
    provider_job_id: str | None = None
    cost_eur: float = 0.0
    duration_ms: int = 0
    retry_count: int = 0
    test_summary: str | None = None
    result_state: JobState = JobState.CHECKPOINTED
    error_class: ErrorClass | None = None
    next_exact_action: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "job_id": self.job_id,
            "parent_run_id": self.parent_run_id,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "host": self.host,
            "worker": self.worker,
            "model_or_provider": self.model_or_provider,
            "tool": self.tool,
            "input_hashes": dict(self.input_hashes),
            "output_hashes": dict(self.output_hashes),
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "provider_job_id": self.provider_job_id,
            "cost_eur": self.cost_eur,
            "duration_ms": self.duration_ms,
            "retry_count": self.retry_count,
            "test_summary": self.test_summary,
            "result_state": self.result_state.value,
            "error_class": self.error_class.value if self.error_class else None,
            "next_exact_action": self.next_exact_action,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "EvidenceRecord":
        return cls(
            run_id=str(data["run_id"]),
            job_id=str(data["job_id"]),
            parent_run_id=(str(data["parent_run_id"]) if data.get("parent_run_id") else None),
            timestamp_start=str(data["timestamp_start"]),
            timestamp_end=str(data["timestamp_end"]),
            host=str(data["host"]),
            worker=str(data["worker"]),
            model_or_provider=(str(data["model_or_provider"]) if data.get("model_or_provider") else None),
            tool=str(data["tool"]),
            input_hashes={str(k): str(v) for k, v in dict(data.get("input_hashes", {})).items()},
            output_hashes={str(k): str(v) for k, v in dict(data.get("output_hashes", {})).items()},
            branch=(str(data["branch"]) if data.get("branch") else None),
            commit_sha=(str(data["commit_sha"]) if data.get("commit_sha") else None),
            provider_job_id=(str(data["provider_job_id"]) if data.get("provider_job_id") else None),
            cost_eur=float(data.get("cost_eur", 0.0)),
            duration_ms=int(data.get("duration_ms", 0)),
            retry_count=int(data.get("retry_count", 0)),
            test_summary=(str(data["test_summary"]) if data.get("test_summary") else None),
            result_state=JobState(str(data.get("result_state", JobState.CHECKPOINTED.value))),
            error_class=(ErrorClass(str(data["error_class"])) if data.get("error_class") else None),
            next_exact_action=(str(data["next_exact_action"]) if data.get("next_exact_action") else None),
        )
