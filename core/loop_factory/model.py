"""Canonical data contracts for the KAI Loop Factory."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Sequence


class AutonomyLevel(str, Enum):
    A0 = "A0"
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    A4 = "A4"
    A5 = "A5"


class JobState(str, Enum):
    QUEUED = "QUEUED"
    BLOCKED = "BLOCKED"
    READY = "READY"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    CHECKPOINTED = "CHECKPOINTED"
    REQUEUE = "REQUEUE"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"
    CANCELLED = "CANCELLED"


class ErrorClass(str, Enum):
    AUTH_REQUIRED = "AUTH_REQUIRED"
    ENV_MISSING = "ENV_MISSING"
    DEPENDENCY_MISSING = "DEPENDENCY_MISSING"
    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"
    TEST_REGRESSION = "TEST_REGRESSION"
    PROVIDER_QUOTA = "PROVIDER_QUOTA"
    PROVIDER_DOWN = "PROVIDER_DOWN"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    LICENSE_BLOCK = "LICENSE_BLOCK"
    NONDETERMINISTIC = "NONDETERMINISTIC"
    IDENTITY_FAIL = "IDENTITY_FAIL"
    CONTINUITY_FAIL = "CONTINUITY_FAIL"
    WRITE_SCOPE_VIOLATION = "WRITE_SCOPE_VIOLATION"
    CANONICAL_BRANCH_GUARD = "CANONICAL_BRANCH_GUARD"
    CHECKPOINT_CORRUPT = "CHECKPOINT_CORRUPT"
    UNKNOWN = "UNKNOWN"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


_SECRET_KEY_FRAGMENTS = ("secret", "password", "token", "api_key", "apikey", "credential")

def _reject_secret_keys(value: Any, path: str = "root") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key).lower()
            if any(fragment in key_text for fragment in _SECRET_KEY_FRAGMENTS):
                raise ValueError(f"Secret-like field is forbidden at {path}.{key}")
            _reject_secret_keys(item, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            _reject_secret_keys(item, f"{path}[{index}]")


@dataclass(slots=True)
class Budget:
    currency: str = "EUR"
    max_cost_eur: float = 0.0
    max_iterations: int = 1
    max_retries: int = 0
    timeout_seconds: int = 60

    def __post_init__(self) -> None:
        if self.currency != "EUR":
            raise ValueError("CELL-000 supports EUR budgets only")
        values = (self.max_cost_eur, self.max_iterations, self.max_retries, self.timeout_seconds)
        if any(value < 0 for value in values):
            raise ValueError("Budget limits cannot be negative")

    def to_dict(self) -> dict[str, object]:
        return {
            "currency": self.currency,
            "max_cost_eur": self.max_cost_eur,
            "max_iterations": self.max_iterations,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "Budget":
        return cls(
            currency=str(data.get("currency", "EUR")),
            max_cost_eur=float(data.get("max_cost_eur", 0.0)),
            max_iterations=int(data.get("max_iterations", 1)),
            max_retries=int(data.get("max_retries", 0)),
            timeout_seconds=int(data.get("timeout_seconds", 60)),
        )


@dataclass(slots=True)
class JobManifest:
    schema_version: int
    job_id: str
    project: str
    cell_type: str
    goal: str
    current_authority_refs: list[str]
    input_refs: list[str]
    input_hashes: dict[str, str]
    dependencies: list[str]
    allowed_tools: list[str]
    write_scope: list[str]
    autonomy_level: AutonomyLevel
    budget: Budget
    state: JobState
    worker: str | None
    attempt: int
    evidence_refs: list[str]
    last_error_class: ErrorClass | None
    next_exact_action: str | None
    created_at: str
    updated_at: str

    @classmethod
    def new(
        cls,
        *,
        job_id: str,
        project: str,
        cell_type: str,
        goal: str,
        write_scope: Sequence[str],
        autonomy_level: AutonomyLevel,
        allowed_tools: Sequence[str],
        budget: Budget,
        current_authority_refs: Sequence[str] = (),
        input_refs: Sequence[str] = (),
        input_hashes: Mapping[str, str] | None = None,
        dependencies: Sequence[str] = (),
    ) -> "JobManifest":
        now = utc_now()
        return cls(
            schema_version=1,
            job_id=job_id,
            project=project,
            cell_type=cell_type,
            goal=goal,
            current_authority_refs=list(current_authority_refs),
            input_refs=list(input_refs),
            input_hashes=dict(input_hashes or {}),
            dependencies=list(dependencies),
            allowed_tools=list(allowed_tools),
            write_scope=list(write_scope),
            autonomy_level=AutonomyLevel(autonomy_level),
            budget=budget,
            state=JobState.QUEUED,
            worker=None,
            attempt=0,
            evidence_refs=[],
            last_error_class=None,
            next_exact_action=None,
            created_at=now,
            updated_at=now,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "job_id": self.job_id,
            "project": self.project,
            "cell_type": self.cell_type,
            "goal": self.goal,
            "current_authority_refs": list(self.current_authority_refs),
            "input_refs": list(self.input_refs),
            "input_hashes": dict(self.input_hashes),
            "dependencies": list(self.dependencies),
            "allowed_tools": list(self.allowed_tools),
            "write_scope": list(self.write_scope),
            "autonomy_level": self.autonomy_level.value,
            "budget": self.budget.to_dict(),
            "state": self.state.value,
            "worker": self.worker,
            "attempt": self.attempt,
            "evidence_refs": list(self.evidence_refs),
            "last_error_class": self.last_error_class.value if self.last_error_class else None,
            "next_exact_action": self.next_exact_action,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "JobManifest":
        _reject_secret_keys(data)
        if int(data.get("schema_version", 0)) != 1:
            raise ValueError("Unsupported job schema_version")
        budget_data = data.get("budget")
        if not isinstance(budget_data, Mapping):
            raise ValueError("budget must be a mapping")
        return cls(
            schema_version=1,
            job_id=str(data["job_id"]),
            project=str(data["project"]),
            cell_type=str(data["cell_type"]),
            goal=str(data["goal"]),
            current_authority_refs=[str(x) for x in data.get("current_authority_refs", [])],
            input_refs=[str(x) for x in data.get("input_refs", [])],
            input_hashes={str(k): str(v) for k, v in dict(data.get("input_hashes", {})).items()},
            dependencies=[str(x) for x in data.get("dependencies", [])],
            allowed_tools=[str(x) for x in data.get("allowed_tools", [])],
            write_scope=[str(x) for x in data.get("write_scope", [])],
            autonomy_level=AutonomyLevel(str(data["autonomy_level"])),
            budget=Budget.from_dict(budget_data),
            state=JobState(str(data.get("state", JobState.QUEUED.value))),
            worker=str(data["worker"]) if data.get("worker") is not None else None,
            attempt=int(data.get("attempt", 0)),
            evidence_refs=[str(x) for x in data.get("evidence_refs", [])],
            last_error_class=(
                ErrorClass(str(data["last_error_class"]))
                if data.get("last_error_class") is not None else None
            ),
            next_exact_action=(
                str(data["next_exact_action"]) if data.get("next_exact_action") is not None else None
            ),
            created_at=str(data["created_at"]),
            updated_at=str(data["updated_at"]),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, payload: str) -> "JobManifest":
        data = json.loads(payload)
        if not isinstance(data, Mapping):
            raise ValueError("Job manifest JSON must contain an object")
        return cls.from_dict(data)


@dataclass(slots=True)
class AttemptRecord:
    run_id: str
    job_id: str
    attempt_no: int
    parent_run_id: str | None
    state: JobState
    worker: str | None
    lease_until: str | None
    timestamp_start: str
    timestamp_end: str | None = None
    retry_count: int = 0
    cost_eur: float = 0.0
    error_class: ErrorClass | None = None
    next_exact_action: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "job_id": self.job_id,
            "attempt_no": self.attempt_no,
            "parent_run_id": self.parent_run_id,
            "state": self.state.value,
            "worker": self.worker,
            "lease_until": self.lease_until,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "retry_count": self.retry_count,
            "cost_eur": self.cost_eur,
            "error_class": self.error_class.value if self.error_class else None,
            "next_exact_action": self.next_exact_action,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "AttemptRecord":
        _reject_secret_keys(data)
        return cls(
            run_id=str(data["run_id"]),
            job_id=str(data["job_id"]),
            attempt_no=int(data["attempt_no"]),
            parent_run_id=str(data["parent_run_id"]) if data.get("parent_run_id") else None,
            state=JobState(str(data["state"])),
            worker=str(data["worker"]) if data.get("worker") else None,
            lease_until=str(data["lease_until"]) if data.get("lease_until") else None,
            timestamp_start=str(data["timestamp_start"]),
            timestamp_end=str(data["timestamp_end"]) if data.get("timestamp_end") else None,
            retry_count=int(data.get("retry_count", 0)),
            cost_eur=float(data.get("cost_eur", 0.0)),
            error_class=(ErrorClass(str(data["error_class"])) if data.get("error_class") else None),
            next_exact_action=(str(data["next_exact_action"]) if data.get("next_exact_action") else None),
        )
