"""SQLite-backed durable state for KAI Loop Factory."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Mapping, TYPE_CHECKING

from .errors import LoopFactoryError
from .model import AttemptRecord, ErrorClass, JobManifest, JobState, utc_now
from .state_machine import assert_transition, is_attempt_end_state, initial_state_for_new_attempt

if TYPE_CHECKING:
    from .evidence import EvidenceRecord


_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY, manifest_json TEXT NOT NULL, state TEXT NOT NULL,
  attempt INTEGER NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS attempts (
  run_id TEXT PRIMARY KEY, job_id TEXT NOT NULL, attempt_no INTEGER NOT NULL,
  parent_run_id TEXT, state TEXT NOT NULL, worker TEXT, lease_until TEXT,
  timestamp_start TEXT NOT NULL, timestamp_end TEXT, retry_count INTEGER NOT NULL DEFAULT 0,
  cost_eur REAL NOT NULL DEFAULT 0, error_class TEXT, next_exact_action TEXT,
  UNIQUE(job_id, attempt_no)
);
"""
_SCHEMA += """
CREATE TABLE IF NOT EXISTS checkpoints (
  checkpoint_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, job_id TEXT NOT NULL,
  sequence INTEGER NOT NULL, payload_json TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL, UNIQUE(run_id, sequence)
);
CREATE TABLE IF NOT EXISTS step_receipts (
  job_id TEXT NOT NULL, attempt_no INTEGER NOT NULL, step_key TEXT NOT NULL,
  input_hash TEXT NOT NULL, output_hash TEXT NOT NULL, evidence_ref TEXT NOT NULL,
  completed_at TEXT NOT NULL,
  PRIMARY KEY(job_id, attempt_no, step_key, input_hash)
);
CREATE TABLE IF NOT EXISTS evidence (
  evidence_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, job_id TEXT NOT NULL,
  record_json TEXT NOT NULL, created_at TEXT NOT NULL
);
"""


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class LoopStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._connection: sqlite3.Connection | None = None

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("LoopStore is not initialized")
        return self._connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.executescript(_SCHEMA)
        self._connection.commit()

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def create_job(self, job: JobManifest) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO jobs(job_id, manifest_json, state, attempt, updated_at) VALUES (?, ?, ?, ?, ?)",
                (job.job_id, job.to_json(), job.state.value, job.attempt, job.updated_at),
            )

    def get_job(self, job_id: str) -> JobManifest:
        row = self.connection.execute(
            "SELECT manifest_json FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        if row is None:
            raise KeyError(job_id)
        return JobManifest.from_json(row["manifest_json"])

    def update_job(self, job: JobManifest) -> None:
        with self.connection:
            cursor = self.connection.execute(
                "UPDATE jobs SET manifest_json=?, state=?, attempt=?, updated_at=? WHERE job_id=?",
                (job.to_json(), job.state.value, job.attempt, job.updated_at, job.job_id),
            )
        if cursor.rowcount != 1:
            raise KeyError(job.job_id)

    def get_latest_attempt(self, job_id: str) -> AttemptRecord | None:
        row = self.connection.execute(
            "SELECT * FROM attempts WHERE job_id=? ORDER BY attempt_no DESC LIMIT 1", (job_id,)
        ).fetchone()
        return self._attempt_from_row(row) if row is not None else None

    def start_attempt(
        self,
        job_id: str,
        worker: str,
        parent_run_id: str | None = None,
    ) -> AttemptRecord:
        job = self.get_job(job_id)
        latest = self.get_latest_attempt(job_id)
        if latest is not None and not is_attempt_end_state(latest.state):
            raise ValueError(f"Job {job_id} already has active attempt {latest.run_id}")
        attempt_no = 1 if latest is None else latest.attempt_no + 1
        if parent_run_id is None and latest is not None:
            parent_run_id = latest.run_id
        attempt = AttemptRecord(
            run_id=uuid.uuid4().hex,
            job_id=job_id,
            attempt_no=attempt_no,
            parent_run_id=parent_run_id,
            state=initial_state_for_new_attempt(),
            worker=worker,
            lease_until=None,
            timestamp_start=utc_now(),
        )
        with self.connection:
            self.connection.execute(
                """INSERT INTO attempts(run_id,job_id,attempt_no,parent_run_id,state,worker,lease_until,
                   timestamp_start,timestamp_end,retry_count,cost_eur,error_class,next_exact_action)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    attempt.run_id, attempt.job_id, attempt.attempt_no, attempt.parent_run_id,
                    attempt.state.value, attempt.worker, attempt.lease_until,
                    attempt.timestamp_start, attempt.timestamp_end, attempt.retry_count,
                    attempt.cost_eur, None, attempt.next_exact_action,
                ),
            )
        job.attempt = attempt_no
        job.worker = worker
        job.state = JobState.READY
        job.updated_at = utc_now()
        self.update_job(job)
        return attempt

    def heartbeat(self, run_id: str, lease_until: str) -> None:
        with self.connection:
            cursor = self.connection.execute(
                "UPDATE attempts SET lease_until=? WHERE run_id=?", (lease_until, run_id)
            )
        if cursor.rowcount != 1:
            raise KeyError(run_id)

    def mark_attempt_state(
        self,
        run_id: str,
        state: JobState,
        *,
        error_class: ErrorClass | None = None,
        next_exact_action: str | None = None,
        cost_eur: float | None = None,
    ) -> None:
        row = self.connection.execute("SELECT * FROM attempts WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        current = JobState(row["state"])
        target = JobState(state)
        if is_attempt_end_state(current) and target != current:
            raise ValueError(f"Attempt {run_id} is immutable after {current.value}")
        if target != current:
            assert_transition(current, target)
        ended_at = utc_now() if is_attempt_end_state(target) else row["timestamp_end"]
        new_cost = row["cost_eur"] if cost_eur is None else float(cost_eur)
        with self.connection:
            self.connection.execute(
                """UPDATE attempts SET state=?, timestamp_end=?, error_class=?,
                   next_exact_action=?, cost_eur=? WHERE run_id=?""",
                (
                    target.value,
                    ended_at,
                    error_class.value if error_class else None,
                    next_exact_action,
                    new_cost,
                    run_id,
                ),
            )
        job = self.get_job(row["job_id"])
        job.state = target
        job.last_error_class = error_class
        job.next_exact_action = next_exact_action
        job.updated_at = utc_now()
        self.update_job(job)

    def append_checkpoint(
        self,
        run_id: str,
        job_id: str,
        payload: Mapping[str, object],
    ) -> str:
        payload_json = _canonical_json(payload)
        digest = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        checkpoint_id = uuid.uuid4().hex
        with self.connection:
            sequence = self._next_checkpoint_sequence(run_id)
            self.connection.execute(
                """INSERT INTO checkpoints(checkpoint_id,run_id,job_id,sequence,payload_json,
                   payload_sha256,created_at) VALUES (?,?,?,?,?,?,?)""",
                (checkpoint_id, run_id, job_id, sequence, payload_json, digest, utc_now()),
            )
        return checkpoint_id

    def latest_checkpoint(self, job_id: str) -> dict[str, object] | None:
        row = self.connection.execute(
            """SELECT payload_json,payload_sha256 FROM checkpoints
               WHERE job_id=? ORDER BY created_at DESC, sequence DESC LIMIT 1""",
            (job_id,),
        ).fetchone()
        if row is None:
            return None
        digest = hashlib.sha256(row["payload_json"].encode("utf-8")).hexdigest()
        if digest != row["payload_sha256"]:
            raise LoopFactoryError(ErrorClass.CHECKPOINT_CORRUPT, f"Checkpoint hash mismatch for {job_id}")
        payload = json.loads(row["payload_json"])
        if not isinstance(payload, dict):
            raise LoopFactoryError(ErrorClass.CHECKPOINT_CORRUPT, "Checkpoint payload is not an object")
        return payload

    def record_step_receipt(
        self,
        job_id: str,
        attempt_no: int,
        step_key: str,
        input_hash: str,
        output_hash: str,
        evidence_ref: str,
    ) -> None:
        try:
            with self.connection:
                self._insert_receipt(job_id, attempt_no, step_key, input_hash, output_hash, evidence_ref)
        except sqlite3.IntegrityError as exc:
            raise ValueError("Step receipt already exists") from exc

    def find_step_receipt(
        self,
        job_id: str,
        attempt_no: int,
        step_key: str,
        input_hash: str,
    ) -> dict[str, object] | None:
        row = self.connection.execute(
            """SELECT * FROM step_receipts
               WHERE job_id=? AND attempt_no=? AND step_key=? AND input_hash=?""",
            (job_id, attempt_no, step_key, input_hash),
        ).fetchone()
        return dict(row) if row is not None else None

    def commit_step(
        self,
        run_id: str,
        job_id: str,
        attempt_no: int,
        step_key: str,
        input_hash: str,
        output_hash: str,
        evidence_ref: str,
        checkpoint_payload: Mapping[str, object],
    ) -> str:
        payload_json = _canonical_json(checkpoint_payload)
        digest = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        checkpoint_id = uuid.uuid4().hex
        try:
            with self.connection:
                self._insert_receipt(job_id, attempt_no, step_key, input_hash, output_hash, evidence_ref)
                sequence = self._next_checkpoint_sequence(run_id)
                self.connection.execute(
                    """INSERT INTO checkpoints(checkpoint_id,run_id,job_id,sequence,payload_json,
                       payload_sha256,created_at) VALUES (?,?,?,?,?,?,?)""",
                    (checkpoint_id, run_id, job_id, sequence, payload_json, digest, utc_now()),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Atomic step commit conflicts with existing receipt/checkpoint") from exc
        return checkpoint_id

    def append_evidence(self, record: "EvidenceRecord") -> None:
        payload = _canonical_json(record.to_dict())
        with self.connection:
            self.connection.execute(
                "INSERT INTO evidence(evidence_id,run_id,job_id,record_json,created_at) VALUES (?,?,?,?,?)",
                (uuid.uuid4().hex, record.run_id, record.job_id, payload, utc_now()),
            )

    def list_evidence(self, job_id: str) -> list["EvidenceRecord"]:
        from .evidence import EvidenceRecord

        rows = self.connection.execute(
            "SELECT record_json FROM evidence WHERE job_id=? ORDER BY created_at, evidence_id",
            (job_id,),
        ).fetchall()
        return [EvidenceRecord.from_dict(json.loads(row["record_json"])) for row in rows]

    def _next_checkpoint_sequence(self, run_id: str) -> int:
        row = self.connection.execute(
            "SELECT COALESCE(MAX(sequence), 0) AS max_sequence FROM checkpoints WHERE run_id=?",
            (run_id,),
        ).fetchone()
        return int(row["max_sequence"]) + 1

    def _insert_receipt(
        self,
        job_id: str,
        attempt_no: int,
        step_key: str,
        input_hash: str,
        output_hash: str,
        evidence_ref: str,
    ) -> None:
        self.connection.execute(
            """INSERT INTO step_receipts(job_id,attempt_no,step_key,input_hash,output_hash,
               evidence_ref,completed_at) VALUES (?,?,?,?,?,?,?)""",
            (job_id, attempt_no, step_key, input_hash, output_hash, evidence_ref, utc_now()),
        )

    @staticmethod
    def _attempt_from_row(row: sqlite3.Row) -> AttemptRecord:
        return AttemptRecord(
            run_id=row["run_id"],
            job_id=row["job_id"],
            attempt_no=int(row["attempt_no"]),
            parent_run_id=row["parent_run_id"],
            state=JobState(row["state"]),
            worker=row["worker"],
            lease_until=row["lease_until"],
            timestamp_start=row["timestamp_start"],
            timestamp_end=row["timestamp_end"],
            retry_count=int(row["retry_count"]),
            cost_eur=float(row["cost_eur"]),
            error_class=ErrorClass(row["error_class"]) if row["error_class"] else None,
            next_exact_action=row["next_exact_action"],
        )
