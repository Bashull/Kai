from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import tempfile
import time
from typing import Any, Callable

from audio_studio.execution import ExecutionBlocked
from audio_studio.transports.gradio_zerogpu import GradioCall

_SECRET_PATTERNS = (
    re.compile(r"(?i)bearer\s+[^\s,;]+"),
    re.compile(r"\bhf_[A-Za-z0-9]{8,}\b"),
    re.compile(r"(?i)(token|api[_-]?key|authorization)=([^&\s]+)"),
)


@dataclass(frozen=True)
class CanaryPermit:
    permit_id: str
    provider_id: str
    call_fingerprint: str
    approved_by: str
    approved_at: str
    one_shot: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CanaryAttemptRecord:
    attempt_id: str
    permit_id: str
    provider_id: str
    status: str
    started_at: str
    elapsed_ms: int
    error_code: str | None = None
    error_message: str | None = None
    output_reference_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CanaryRunResult:
    record: CanaryAttemptRecord
    output: Any = None


def fingerprint_call(call: GradioCall) -> str:
    payload = json.dumps(
        call.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def issue_manual_permit(
    call: GradioCall,
    *,
    permit_id: str,
    approved_by: str,
    approved_at: str | None = None,
) -> CanaryPermit:
    if not permit_id.strip() or not approved_by.strip():
        raise ValueError("permit_id and approved_by are required")
    return CanaryPermit(
        permit_id=permit_id.strip(),
        provider_id="ace-step-1.5-zerogpu",
        call_fingerprint=fingerprint_call(call),
        approved_by=approved_by.strip(),
        approved_at=approved_at or datetime.now(UTC).isoformat(),
    )


class CanaryEventJournal:
    """Append-only NDJSON attempt journal containing sanitized records only."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def append(self, record: CanaryAttemptRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(
            record.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()

    def read_all(self) -> list[CanaryAttemptRecord]:
        if not self.path.exists():
            return []
        records = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(CanaryAttemptRecord(**json.loads(line)))
        return records


class CanaryPermitLedger:
    """Durable one-shot permit ledger. It stores identifiers, never credentials."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def consume(self, permit: CanaryPermit, call: GradioCall) -> None:
        if not permit.one_shot:
            raise ExecutionBlocked("ONE_SHOT_PERMIT_REQUIRED")
        if permit.provider_id != "ace-step-1.5-zerogpu":
            raise ExecutionBlocked("WRONG_PROVIDER_PERMIT")
        if permit.call_fingerprint != fingerprint_call(call):
            raise ExecutionBlocked("PERMIT_CALL_MISMATCH")
        state = self._load()
        if permit.permit_id in state["consumed_permits"]:
            raise ExecutionBlocked("PERMIT_ALREADY_CONSUMED")
        state["consumed_permits"][permit.permit_id] = {
            "provider_id": permit.provider_id,
            "call_fingerprint": permit.call_fingerprint,
            "approved_by": permit.approved_by,
            "approved_at": permit.approved_at,
            "consumed_at": datetime.now(UTC).isoformat(),
        }
        self._write_atomic(state)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": "1.0.0", "consumed_permits": {}}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if data.get("schema_version") != "1.0.0":
            raise ValueError("unsupported permit ledger schema")
        if not isinstance(data.get("consumed_permits"), dict):
            raise ValueError("invalid permit ledger")
        return data

    def _write_atomic(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.path.parent, delete=False
        ) as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            temp_path = Path(handle.name)
        temp_path.replace(self.path)


def run_governed_canary(
    call: GradioCall,
    permit: CanaryPermit,
    ledger: CanaryPermitLedger,
    submitter: Callable[[GradioCall], Any],
    *,
    attempt_id: str,
    event_sink: Callable[[CanaryAttemptRecord], None] | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    now: Callable[[], str] | None = None,
) -> CanaryRunResult:
    """Consume one manual permit and make at most one submission."""
    if call.max_attempts != 1:
        raise ExecutionBlocked("AUTOMATIC_RETRIES_FORBIDDEN")
    if not attempt_id.strip():
        raise ValueError("attempt_id is required")
    ledger.consume(permit, call)
    timestamp = now or (lambda: datetime.now(UTC).isoformat())
    started_at = timestamp()
    start = monotonic()
    submitted = CanaryAttemptRecord(
        attempt_id, permit.permit_id, permit.provider_id, "SUBMITTED", started_at, 0
    )
    if event_sink:
        event_sink(submitted)
    try:
        output = submitter(call)
    except Exception as exc:
        elapsed_ms = max(0, round((monotonic() - start) * 1000))
        message = sanitize_error(str(exc))
        failed = CanaryAttemptRecord(
            attempt_id,
            permit.permit_id,
            permit.provider_id,
            "FAILED",
            started_at,
            elapsed_ms,
            classify_error(message),
            message,
        )
        if event_sink:
            event_sink(failed)
        return CanaryRunResult(failed)
    elapsed_ms = max(0, round((monotonic() - start) * 1000))
    succeeded = CanaryAttemptRecord(
        attempt_id,
        permit.permit_id,
        permit.provider_id,
        "SUCCEEDED",
        started_at,
        elapsed_ms,
        output_reference_count=_count_output_references(output),
    )
    if event_sink:
        event_sink(succeeded)
    return CanaryRunResult(succeeded, output)


def classify_error(message: str) -> str:
    lowered = message.lower()
    if "gpu task aborted" in lowered:
        return "UPSTREAM_GPU_ABORTED"
    if "quota" in lowered or "exceeded your gpu quota" in lowered:
        return "QUOTA_EXHAUSTED"
    if "queue" in lowered:
        return "QUEUE_FAILURE"
    if "timeout" in lowered or "timed out" in lowered:
        return "UPSTREAM_TIMEOUT"
    return "UPSTREAM_ERROR"


def sanitize_error(message: str) -> str:
    sanitized = message.replace("\r", " ").replace("\n", " ").strip()
    for pattern in _SECRET_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    return sanitized[:240]


def _count_output_references(output: Any) -> int:
    if output is None:
        return 0
    if isinstance(output, (str, Path)):
        return 1
    if isinstance(output, (list, tuple, set)):
        return sum(_count_output_references(item) for item in output)
    if isinstance(output, dict):
        return sum(_count_output_references(item) for item in output.values())
    return 0
