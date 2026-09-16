"""Drive-ready checkpoint rendering without a Drive dependency."""
from __future__ import annotations

from typing import Mapping, Sequence

from .evidence import EvidenceRecord
from .model import AttemptRecord, JobManifest


def build_drive_checkpoint_payload(
    job: JobManifest,
    attempt: AttemptRecord | None,
    evidence: Sequence[EvidenceRecord],
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "job_id": job.job_id,
        "project": job.project,
        "cell_type": job.cell_type,
        "state": job.state.value,
        "attempt": job.attempt,
        "latest_run_id": attempt.run_id if attempt else None,
        "latest_attempt_state": attempt.state.value if attempt else None,
        "last_error_class": job.last_error_class.value if job.last_error_class else None,
        "evidence_count": len(evidence),
        "evidence_refs": list(job.evidence_refs),
        "next_exact_action": job.next_exact_action or "inspect job state",
        "updated_at": job.updated_at,
    }


def render_drive_checkpoint_markdown(payload: Mapping[str, object]) -> str:
    job_id = payload.get("job_id", "unknown")
    state = payload.get("state", "UNKNOWN")
    next_action = payload.get("next_exact_action", "inspect job state")
    attempt = payload.get("attempt", "?")
    evidence_count = payload.get("evidence_count", "?")
    return (
        f"# Loop Factory checkpoint · {job_id}\n\n"
        f"- State: `{state}`\n"
        f"- Attempt: `{attempt}`\n"
        f"- Evidence records: `{evidence_count}`\n"
        f"- Next exact action: {next_action}\n"
    )
