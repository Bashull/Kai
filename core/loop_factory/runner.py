"""One-iteration durable runner for CELL-000."""
from __future__ import annotations

import json
import platform
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Mapping

from .errors import LoopFactoryError
from .evidence import EvidenceRecord, sha256_text
from .guards import assert_noncanonical_branch, assert_write_scope
from .model import ErrorClass, JobManifest, JobState, utc_now
from .state_machine import is_attempt_end_state, is_terminal
from .store import LoopStore
from .workers import StepContext, StepOutcome, Worker


@dataclass(frozen=True, slots=True)
class RunResult:
    run_id: str
    state: JobState
    evidence_ref: str | None
    next_exact_action: str | None


def _stable_input_hash(job: JobManifest) -> str:
    payload = {
        "job_id": job.job_id,
        "goal": job.goal,
        "input_refs": job.input_refs,
        "input_hashes": job.input_hashes,
        "dependencies": job.dependencies,
    }
    return sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _git_commit_sha() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value or None


class LoopRunner:
    def __init__(self, store: LoopStore, workers: Mapping[str, Worker]) -> None:
        self.store = store
        self.workers = dict(workers)

    def run_once(
        self,
        job_id: str,
        *,
        branch: str,
        worker_id: str = "demo-file",
        after_checkpoint: Callable[[], None] | None = None,
    ) -> RunResult:
        job = self.store.get_job(job_id)
        assert_noncanonical_branch(branch)
        worker = self._get_worker(job, worker_id)
        sandbox = self._worker_sandbox(worker)
        assert_write_scope(sandbox, [Path(item) for item in job.write_scope])
        self._assert_preflight_budget(job, worker)

        latest = self.store.get_latest_attempt(job_id)
        if latest is not None and latest.state is JobState.SUCCEEDED:
            return RunResult(latest.run_id, JobState.SUCCEEDED, None, latest.next_exact_action)
        if latest is not None and latest.state in {JobState.FAILED, JobState.QUARANTINED, JobState.CANCELLED}:
            if job.state is not JobState.REQUEUE:
                return RunResult(latest.run_id, latest.state, None, latest.next_exact_action)

        if latest is None or is_attempt_end_state(latest.state):
            if job.attempt >= job.budget.max_iterations:
                job.state = JobState.QUARANTINED
                job.last_error_class = ErrorClass.BUDGET_EXCEEDED
                job.next_exact_action = "increase iteration budget or inspect the failure"
                job.updated_at = utc_now()
                self.store.update_job(job)
                return RunResult("", job.state, None, job.next_exact_action)
            attempt = self.store.start_attempt(job_id, worker_id)
        else:
            attempt = latest
            if attempt.state is JobState.RUNNING and not self._lease_expired(attempt.lease_until):
                raise LoopFactoryError(
                    ErrorClass.UNKNOWN,
                    f"Attempt {attempt.run_id} still holds an active lease",
                    retryable=True,
                )

        if attempt.state is JobState.READY:
            self.store.mark_attempt_state(attempt.run_id, JobState.RUNNING)
            attempt = self.store.get_latest_attempt(job_id)
        lease_until = (datetime.now(timezone.utc) + timedelta(
            seconds=max(1, job.budget.timeout_seconds)
        )).isoformat().replace("+00:00", "Z")
        self.store.heartbeat(attempt.run_id, lease_until)

        input_hash = _stable_input_hash(job)
        step_key = f"{worker_id}/act"
        receipt = self.store.find_step_receipt(
            job_id, attempt.attempt_no, step_key, input_hash
        )
        outcome: StepOutcome | None = None
        duration_ms = 0

        if receipt is None:
            context = StepContext(job, attempt.run_id, sandbox, input_hash)
            started = time.monotonic()
            try:
                outcome = worker.run(context)
            except Exception as exc:
                return self._handle_pre_receipt_failure(job, attempt.run_id, exc)
            duration_ms = int((time.monotonic() - started) * 1000)
            evidence_ref = f"{attempt.run_id}:{step_key}:{input_hash[:16]}"
            checkpoint_payload = {
                "phase": JobState.CHECKPOINTED.value,
                "step_key": step_key,
                "input_hash": input_hash,
                "output_hash": outcome.output_hash,
                "evidence_ref": evidence_ref,
                "cost_eur": outcome.cost_eur,
                "duration_ms": duration_ms,
            }
            self.store.commit_step(
                attempt.run_id, job_id, attempt.attempt_no, step_key,
                input_hash, outcome.output_hash, evidence_ref, checkpoint_payload,
            )
            current = self.store.get_latest_attempt(job_id)
            if current is not None and current.state is JobState.RUNNING:
                self.store.mark_attempt_state(attempt.run_id, JobState.CHECKPOINTED)
            if after_checkpoint is not None:
                after_checkpoint()
            receipt = self.store.find_step_receipt(
                job_id, attempt.attempt_no, step_key, input_hash
            )
        else:
            evidence_ref = str(receipt["evidence_ref"])
            checkpoint = self.store.latest_checkpoint(job_id) or {}
            duration_ms = int(checkpoint.get("duration_ms", 0))
            outcome = StepOutcome(
                output_hash=str(receipt["output_hash"]),
                evidence_summary="recovered from durable receipt",
                cost_eur=float(checkpoint.get("cost_eur", 0.0)),
                verified=True,
            )
            current = self.store.get_latest_attempt(job_id)
            if current is not None and current.state is JobState.RUNNING:
                self.store.mark_attempt_state(attempt.run_id, JobState.CHECKPOINTED)

        assert outcome is not None
        if duration_ms > job.budget.timeout_seconds * 1000:
            return self._quarantine_after_receipt(
                attempt.run_id,
                ErrorClass.UNKNOWN,
                "worker exceeded timeout after producing a durable effect",
                outcome.cost_eur,
            )
        if outcome.cost_eur > job.budget.max_cost_eur:
            return self._quarantine_after_receipt(
                attempt.run_id,
                ErrorClass.BUDGET_EXCEEDED,
                "worker exceeded the job cost ceiling after producing a durable effect",
                outcome.cost_eur,
            )

        self.store.mark_attempt_state(attempt.run_id, JobState.VERIFYING)
        context = StepContext(job, attempt.run_id, sandbox, input_hash)
        verified = bool(outcome.verified)
        verifier = getattr(worker, "verify", None)
        if callable(verifier):
            verified = verified and bool(verifier(context, outcome.output_hash))
        if not verified:
            return self._quarantine_after_receipt(
                attempt.run_id,
                ErrorClass.TEST_REGRESSION,
                "durable output failed verification",
                outcome.cost_eur,
            )

        next_action = "review evidence for promotion"
        evidence = EvidenceRecord(
            run_id=attempt.run_id,
            job_id=job_id,
            parent_run_id=attempt.parent_run_id,
            timestamp_start=attempt.timestamp_start,
            timestamp_end=utc_now(),
            host=platform.node() or "unknown-host",
            worker=worker_id,
            model_or_provider=None,
            tool=worker_id,
            input_hashes={"step": input_hash},
            output_hashes={"step": outcome.output_hash},
            branch=branch,
            commit_sha=_git_commit_sha(),
            provider_job_id=None,
            cost_eur=outcome.cost_eur,
            duration_ms=duration_ms,
            retry_count=max(0, attempt.attempt_no - 1),
            test_summary=outcome.evidence_summary,
            result_state=JobState.SUCCEEDED,
            error_class=None,
            next_exact_action=next_action,
        )
        self.store.append_evidence(evidence)
        self.store.mark_attempt_state(attempt.run_id, JobState.CHECKPOINTED)
        self.store.mark_attempt_state(
            attempt.run_id,
            JobState.SUCCEEDED,
            next_exact_action=next_action,
            cost_eur=outcome.cost_eur,
        )
        final_job = self.store.get_job(job_id)
        if evidence_ref not in final_job.evidence_refs:
            final_job.evidence_refs.append(evidence_ref)
        final_job.next_exact_action = next_action
        final_job.updated_at = utc_now()
        self.store.update_job(final_job)
        return RunResult(attempt.run_id, JobState.SUCCEEDED, evidence_ref, next_action)

    def _get_worker(self, job: JobManifest, worker_id: str) -> Worker:
        if worker_id not in job.allowed_tools:
            raise LoopFactoryError(
                ErrorClass.AUTH_REQUIRED,
                f"Worker {worker_id!r} is not allowed by job {job.job_id}",
            )
        try:
            return self.workers[worker_id]
        except KeyError as exc:
            raise LoopFactoryError(
                ErrorClass.DEPENDENCY_MISSING,
                f"Worker {worker_id!r} is not registered",
                retryable=False,
            ) from exc

    @staticmethod
    def _worker_sandbox(worker: Worker) -> Path:
        value = getattr(worker, "sandbox", None)
        if value is None:
            raise LoopFactoryError(
                ErrorClass.ENV_MISSING,
                "Mutating CELL-000 workers must expose a sandbox path",
            )
        return Path(value)

    @staticmethod
    def _assert_preflight_budget(job: JobManifest, worker: Worker) -> None:
        estimated = float(getattr(worker, "estimated_cost_eur", 0.0))
        if estimated < 0:
            raise LoopFactoryError(ErrorClass.BUDGET_EXCEEDED, "Negative estimated cost is invalid")
        if estimated > job.budget.max_cost_eur:
            raise LoopFactoryError(
                ErrorClass.BUDGET_EXCEEDED,
                f"Estimated cost {estimated} EUR exceeds job ceiling {job.budget.max_cost_eur} EUR",
            )

    @staticmethod
    def _lease_expired(lease_until: str | None) -> bool:
        expiry = _parse_utc(lease_until)
        if expiry is None:
            return True
        return expiry <= datetime.now(timezone.utc)

    def _handle_pre_receipt_failure(
        self,
        job: JobManifest,
        run_id: str,
        exc: Exception,
    ) -> RunResult:
        attempt = self.store.get_latest_attempt(job.job_id)
        if attempt is None:
            raise RuntimeError("Attempt disappeared during failure handling") from exc
        if attempt.attempt_no <= job.budget.max_retries:
            state = JobState.REQUEUE
            next_action = "retry in a fresh attempt after inspecting UNKNOWN failure"
        else:
            state = JobState.QUARANTINED
            next_action = "inspect UNKNOWN failure before any further execution"
        self.store.mark_attempt_state(
            run_id,
            state,
            error_class=ErrorClass.UNKNOWN,
            next_exact_action=next_action,
        )
        return RunResult(run_id, state, None, next_action)

    def _quarantine_after_receipt(
        self,
        run_id: str,
        error_class: ErrorClass,
        next_action: str,
        cost_eur: float,
    ) -> RunResult:
        self.store.mark_attempt_state(
            run_id,
            JobState.QUARANTINED,
            error_class=error_class,
            next_exact_action=next_action,
            cost_eur=cost_eur,
        )
        return RunResult(run_id, JobState.QUARANTINED, None, next_action)
