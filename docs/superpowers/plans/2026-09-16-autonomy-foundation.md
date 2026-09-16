# KAI Autonomy Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build CELL-000, a dependency-light, restart-safe autonomy substrate that persists bounded jobs, enforces write/permission/budget guards, executes one idempotent iteration at a time, records evidence, and survives interruption without depending on Drive or any hosted orchestration service.

**Architecture:** Add an isolated Python package at `core/loop_factory/` that follows the repository's existing dataclass/Path/JSON style. The control plane uses only Python standard-library facilities for CELL-000: `dataclasses`, `enum`, `json`, `sqlite3`, `argparse`, `hashlib`, `subprocess`, `pathlib`, and `unittest`. SQLite is the durable authority for jobs, attempts, checkpoints, idempotency receipts, and evidence; external systems are represented through narrow worker/capability interfaces and Drive receives rendered checkpoint payloads only through an output adapter.

**Tech Stack:** Python 3.10+ standard library, SQLite (`sqlite3`), `unittest`, Git, GitHub Actions Ubuntu runners. CI validates Python 3.11 and 3.12.

**Spec:** `docs/superpowers/specs/2026-09-16-autonomy-foundation-design.md`

## Global Constraints

- `REUSE -> ADAPT -> COMPOSE -> ACQUIRE -> BUILD`.
- One cell owns one clear objective and one write scope.
- Direct implementation writes to `main` or `master` are forbidden and must fail before mutation.
- All autonomous source changes occur in isolated branches/worktrees and candidate changes enter through PRs.
- SQLite first; no Postgres, Redis, Kafka, Temporal, LangGraph, or hosted orchestration dependency in CELL-000.
- No plaintext credentials in source, job manifests, SQLite payloads, checkpoints, evidence, or logs.
- Every loop has explicit budget, timeout, max iterations, max retries, and terminal states.
- `SUCCEEDED`, `FAILED`, `QUARANTINED`, and `CANCELLED` are terminal for an attempt; requeue creates a new immutable attempt.
- Verification evidence is required before BUILD/REPAIR/PROMOTION jobs can reach `SUCCEEDED`.
- Write-scope and canonical-branch checks run before filesystem mutation.
- Provider/tool permissions are upper bounds; Loop Factory policy is narrower.
- GitHub-hosted runners are used for CI; do not attach a self-hosted runner to an untrusted public-PR path.
- Drive is not required for core execution; CELL-000 only emits Drive-ready checkpoint payloads.
- Runtime SQLite and sandbox artifacts live under `.kai-loop/` by default and are ignored by Git.

---

## File Structure

### New package

- `core/loop_factory/__init__.py` — public CELL-000 API only.
- `core/loop_factory/__main__.py` — `python -m core.loop_factory` entry point.
- `core/loop_factory/model.py` — enums and immutable/serializable job/attempt/budget records.
- `core/loop_factory/errors.py` — typed operational failures mapped to the canonical error taxonomy.
- `core/loop_factory/state_machine.py` — legal job/attempt transitions and terminal-state rules.
- `core/loop_factory/guards.py` — canonical-branch and write-scope fail-closed guards.
- `core/loop_factory/policy.py` — autonomy, cost, promotion, destructive/security policy decisions.
- `core/loop_factory/store.py` — SQLite schema, transactions, jobs, attempts, checkpoints, step receipts.
- `core/loop_factory/evidence.py` — structured evidence contract and SHA-256 helpers.
- `core/loop_factory/capabilities.py` — FREE-FIRST worker capability registry and deterministic candidate ranking.
- `core/loop_factory/workers.py` — worker protocol plus deterministic demo worker for CELL-000 acceptance.
- `core/loop_factory/runner.py` — one-iteration restore/act/verify/checkpoint/evidence/retry engine.
- `core/loop_factory/writeback.py` — Drive-ready JSON/Markdown checkpoint rendering with no Drive dependency.
- `core/loop_factory/cli.py` — create/show/run-once/checkpoint/requeue/cancel/workers commands.

### Tests

- `tests/loop_factory/__init__.py`
- `tests/loop_factory/test_model.py`
- `tests/loop_factory/test_state_machine.py`
- `tests/loop_factory/test_policy_guards.py`
- `tests/loop_factory/test_store.py`
- `tests/loop_factory/test_capabilities.py`
- `tests/loop_factory/test_runner.py`
- `tests/loop_factory/test_cli.py`
- `tests/loop_factory/test_cell000_acceptance.py`

### CI/docs/config

- `.github/workflows/test-loop-factory.yml` — focused standard-library CI on Python 3.11/3.12.
- `docs/loop_factory/CELL_000_RUNBOOK.md` — local/Termux/PC usage, recovery, evidence, known limits.
- `.gitignore` — add `.kai-loop/`, `*.loopfactory.db`, and `*.loopfactory.db-*` only.

Do not modify the React UI or existing autonomous modules during CELL-000. Do not export Loop Factory from `core/__init__.py` yet; callers use `core.loop_factory` explicitly so the new boundary remains independently removable and testable.

---

### Task 1: Canonical Models, Error Taxonomy, and Serialization

**Files:**
- Create: `core/loop_factory/__init__.py`
- Create: `core/loop_factory/model.py`
- Create: `core/loop_factory/errors.py`
- Create: `tests/loop_factory/__init__.py`
- Create: `tests/loop_factory/test_model.py`

**Interfaces:**
- Produces: `AutonomyLevel`, `JobState`, `ErrorClass`, `Budget`, `JobManifest`, `AttemptRecord`, `utc_now()`, `LoopFactoryError`.
- `JobManifest.to_dict() -> dict[str, object]`
- `JobManifest.from_dict(data: Mapping[str, object]) -> JobManifest`
- `JobManifest.to_json() -> str`
- `JobManifest.from_json(payload: str) -> JobManifest`
- Later tasks import these exact names.

- [ ] **Step 1: Write failing model round-trip and secret-rejection tests**

```python
# tests/loop_factory/test_model.py
import json
import unittest

from core.loop_factory.model import AutonomyLevel, Budget, JobManifest, JobState


class JobManifestTests(unittest.TestCase):
    def make_job(self) -> JobManifest:
        return JobManifest.new(
            job_id="CELL-000-DEMO",
            project="KAI_LOOP_FACTORY",
            cell_type="BUILD",
            goal="Create deterministic demo output",
            write_scope=[".kai-loop/sandboxes/CELL-000-DEMO"],
            autonomy_level=AutonomyLevel.A2,
            allowed_tools=["demo-file"],
            budget=Budget(max_cost_eur=0.0, max_iterations=3, max_retries=2, timeout_seconds=60),
        )

    def test_json_round_trip_preserves_contract(self):
        job = self.make_job()
        restored = JobManifest.from_json(job.to_json())
        self.assertEqual(restored, job)
        self.assertEqual(restored.state, JobState.QUEUED)
        self.assertEqual(restored.budget.currency, "EUR")

    def test_manifest_rejects_plaintext_secret_fields(self):
        payload = self.make_job().to_dict()
        payload["api_key"] = "sk-not-allowed"
        with self.assertRaises(ValueError):
            JobManifest.from_dict(payload)

    def test_serialized_manifest_is_valid_json(self):
        parsed = json.loads(self.make_job().to_json())
        self.assertEqual(parsed["schema_version"], 1)
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python -m unittest tests.loop_factory.test_model -v
```

Expected: import failure because `core.loop_factory.model` does not exist.

- [ ] **Step 3: Implement the canonical types with no external dependency**

Use `class X(str, Enum)` rather than `StrEnum` so Python 3.10 remains supported. Define exactly:

```python
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
```

`ErrorClass` must contain exactly the taxonomy from the spec. `Budget` fields are `currency`, `max_cost_eur`, `max_iterations`, `max_retries`, `timeout_seconds`. `JobManifest.new()` initializes empty refs/hashes/dependencies/evidence, state `QUEUED`, attempt `0`, and UTC timestamps. Reject unknown top-level fields whose lowercase name contains `secret`, `password`, `token`, `api_key`, `apikey`, or `credential`; reject non-EUR currency for CELL-000 and negative limits.

`LoopFactoryError` stores `error_class: ErrorClass`, `message: str`, and optional `retryable: bool`.

- [ ] **Step 4: Run focused tests**

```bash
python -m unittest tests.loop_factory.test_model -v
```

Expected: PASS.

- [ ] **Step 5: Commit the independently testable contract**

```bash
git add core/loop_factory tests/loop_factory

git commit -m "feat(loop-factory): add CELL-000 job contract"
```

---

### Task 2: Deterministic State Machine

**Files:**
- Create: `core/loop_factory/state_machine.py`
- Create: `tests/loop_factory/test_state_machine.py`

**Interfaces:**
- Consumes: `JobState`, `LoopFactoryError`, `ErrorClass`.
- Produces: `TERMINAL_STATES`, `is_terminal(state) -> bool`, `assert_transition(current, target) -> None`, `next_attempt_state(previous) -> JobState`.

- [ ] **Step 1: Write failing transition tests**

```python
# tests/loop_factory/test_state_machine.py
import unittest

from core.loop_factory.model import ErrorClass, JobState
from core.loop_factory.errors import LoopFactoryError
from core.loop_factory.state_machine import assert_transition, is_terminal


class StateMachineTests(unittest.TestCase):
    def test_happy_path_is_legal(self):
        path = [
            JobState.QUEUED,
            JobState.READY,
            JobState.RUNNING,
            JobState.VERIFYING,
            JobState.CHECKPOINTED,
            JobState.SUCCEEDED,
        ]
        for current, target in zip(path, path[1:]):
            assert_transition(current, target)

    def test_terminal_state_cannot_transition(self):
        self.assertTrue(is_terminal(JobState.SUCCEEDED))
        with self.assertRaises(LoopFactoryError) as ctx:
            assert_transition(JobState.SUCCEEDED, JobState.RUNNING)
        self.assertEqual(ctx.exception.error_class, ErrorClass.UNKNOWN)

    def test_running_can_be_requeued_after_recoverable_failure(self):
        assert_transition(JobState.RUNNING, JobState.REQUEUE)
```

- [ ] **Step 2: Run and confirm failure**

```bash
python -m unittest tests.loop_factory.test_state_machine -v
```

Expected: import failure for `state_machine`.

- [ ] **Step 3: Implement a closed transition map**

Legal transitions:

```text
QUEUED -> READY | BLOCKED | CANCELLED
BLOCKED -> READY | CANCELLED
READY -> RUNNING | CANCELLED
RUNNING -> VERIFYING | CHECKPOINTED | REQUEUE | FAILED | QUARANTINED | CANCELLED
VERIFYING -> CHECKPOINTED | REQUEUE | FAILED | QUARANTINED | CANCELLED
CHECKPOINTED -> RUNNING | VERIFYING | SUCCEEDED | REQUEUE | FAILED | QUARANTINED | CANCELLED
REQUEUE -> READY | CANCELLED
```

Terminal states have no outgoing transition. Raise `LoopFactoryError(ErrorClass.UNKNOWN, ...)` on illegal transitions. `next_attempt_state()` accepts only a prior `REQUEUE`, `FAILED`, or `QUARANTINED` job history entry and returns `READY`; attempts themselves remain immutable in storage.

- [ ] **Step 4: Run tests**

```bash
python -m unittest tests.loop_factory.test_state_machine -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/loop_factory/state_machine.py tests/loop_factory/test_state_machine.py
git commit -m "feat(loop-factory): enforce deterministic state transitions"
```

---

### Task 3: Fail-Closed Repository and Write-Scope Guards

**Files:**
- Create: `core/loop_factory/guards.py`
- Create: `tests/loop_factory/test_policy_guards.py`

**Interfaces:**
- Produces: `detect_git_branch(repo_root: Path) -> str`, `assert_noncanonical_branch(branch: str, canonical_branches: AbstractSet[str] = {"main", "master"}) -> None`, `assert_write_scope(target: Path, scopes: Sequence[Path]) -> None`.
- All later mutation paths call these functions before writing.

- [ ] **Step 1: Write failing guard tests, including the connector incident**

```python
# tests/loop_factory/test_policy_guards.py
import tempfile
import unittest
from pathlib import Path

from core.loop_factory.errors import LoopFactoryError
from core.loop_factory.model import ErrorClass
from core.loop_factory.guards import assert_noncanonical_branch, assert_write_scope


class GuardTests(unittest.TestCase):
    def test_main_and_master_fail_closed(self):
        for branch in ("main", "master"):
            with self.assertRaises(LoopFactoryError) as ctx:
                assert_noncanonical_branch(branch)
            self.assertEqual(ctx.exception.error_class, ErrorClass.CANONICAL_BRANCH_GUARD)

    def test_feature_branch_is_allowed(self):
        assert_noncanonical_branch("feat/loop-factory-cell-000")

    def test_target_outside_scope_is_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            allowed = root / "sandbox"
            outside = root / "main.py"
            with self.assertRaises(LoopFactoryError) as ctx:
                assert_write_scope(outside, [allowed])
            self.assertEqual(ctx.exception.error_class, ErrorClass.WRITE_SCOPE_VIOLATION)
            self.assertFalse(outside.exists())
```

- [ ] **Step 2: Verify failure**

```bash
python -m unittest tests.loop_factory.test_policy_guards.GuardTests -v
```

Expected: import failure for `guards`.

- [ ] **Step 3: Implement path-safe guards**

Resolve both target and scopes with `Path.resolve(strict=False)`. A target is allowed only when `target == scope` or `scope in target.parents`. Empty write scope rejects every mutation. `detect_git_branch()` runs:

```bash
git -C <repo_root> rev-parse --abbrev-ref HEAD
```

If Git fails, output is empty, or output is `HEAD`, raise `LoopFactoryError(ErrorClass.ENV_MISSING, ..., retryable=False)` rather than guessing. A mutation caller must never silently substitute `main` or the repository default branch.

- [ ] **Step 4: Run focused tests**

```bash
python -m unittest tests.loop_factory.test_policy_guards.GuardTests -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/loop_factory/guards.py tests/loop_factory/test_policy_guards.py
git commit -m "feat(loop-factory): fail closed on canonical and out-of-scope writes"
```

---

### Task 4: Autonomy and Budget Policy Engine

**Files:**
- Create: `core/loop_factory/policy.py`
- Modify: `tests/loop_factory/test_policy_guards.py`

**Interfaces:**
- Produces: `ActionRequest`, `PolicyDecision`, `PolicyEngine.evaluate(job, action, *, explicit_authorization=False) -> PolicyDecision`.
- Consumes branch and path guards from Task 3.

- [ ] **Step 1: Add failing policy tests**

```python
from core.loop_factory.model import AutonomyLevel, Budget, ErrorClass, JobManifest
from core.loop_factory.policy import ActionRequest, PolicyEngine


class PolicyTests(unittest.TestCase):
    def make_job(self, level=AutonomyLevel.A2, max_cost=0.0):
        return JobManifest.new(
            job_id="policy-test",
            project="KAI_LOOP_FACTORY",
            cell_type="BUILD",
            goal="policy test",
            write_scope=["/tmp/kai-sandbox"],
            autonomy_level=level,
            allowed_tools=["demo-file"],
            budget=Budget(max_cost_eur=max_cost, max_iterations=2, max_retries=1, timeout_seconds=30),
        )

    def test_cost_above_job_budget_is_denied(self):
        decision = PolicyEngine().evaluate(
            self.make_job(max_cost=0.0),
            ActionRequest(name="gpu", estimated_cost_eur=0.01, mutation=False),
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.error_class, ErrorClass.BUDGET_EXCEEDED)

    def test_promotion_requires_explicit_authorization(self):
        decision = PolicyEngine().evaluate(
            self.make_job(level=AutonomyLevel.A4),
            ActionRequest(name="merge", promotion=True, mutation=True, target_branch="feat/candidate"),
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.error_class, ErrorClass.AUTH_REQUIRED)

    def test_a5_security_action_cannot_self_authorize(self):
        job = self.make_job(level=AutonomyLevel.A5)
        action = ActionRequest(name="rotate-secret", security_sensitive=True, mutation=True)
        self.assertFalse(PolicyEngine().evaluate(job, action).allowed)
        self.assertTrue(PolicyEngine().evaluate(job, action, explicit_authorization=True).allowed)
```

- [ ] **Step 2: Run and confirm failure**

```bash
python -m unittest tests.loop_factory.test_policy_guards.PolicyTests -v
```

Expected: import failure for `policy`.

- [ ] **Step 3: Implement policy evaluation order**

Evaluate in this order: malformed/negative cost -> declared budget -> autonomy ceiling -> destructive/security/A5 authorization -> A4 promotion authorization -> canonical branch guard -> write-scope guard -> allow. Return a `PolicyDecision`; only guard helpers raise during low-level preflight. Never manufacture `explicit_authorization=True` inside the policy engine.

- [ ] **Step 4: Run all guard/policy tests**

```bash
python -m unittest tests.loop_factory.test_policy_guards -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/loop_factory/policy.py tests/loop_factory/test_policy_guards.py
git commit -m "feat(loop-factory): add autonomy and budget policy engine"
```

---

### Task 5: SQLite Durable Store, Attempts, Checkpoints, and Idempotency Receipts

**Files:**
- Create: `core/loop_factory/store.py`
- Create: `tests/loop_factory/test_store.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `LoopStore` with `initialize()`, `create_job()`, `get_job()`, `update_job()`, `start_attempt()`, `get_latest_attempt()`, `heartbeat()`, `mark_attempt_state()`, `append_checkpoint()`, `latest_checkpoint()`, `find_step_receipt()`, `commit_step()`, `append_evidence()`, `list_evidence()`.
- `commit_step()` atomically persists a completed step receipt and its checkpoint in one SQLite transaction.

- [ ] **Step 1: Write failing durability and immutability tests**

```python
# tests/loop_factory/test_store.py
import tempfile
import unittest
from pathlib import Path

from core.loop_factory.model import AutonomyLevel, Budget, JobManifest, JobState
from core.loop_factory.store import LoopStore


class LoopStoreTests(unittest.TestCase):
    def test_job_survives_store_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "state.loopfactory.db"
            job = JobManifest.new(
                job_id="persist-me",
                project="KAI_LOOP_FACTORY",
                cell_type="BUILD",
                goal="persist",
                write_scope=[str(Path(tmp) / "sandbox")],
                autonomy_level=AutonomyLevel.A2,
                allowed_tools=["demo-file"],
                budget=Budget(max_cost_eur=0, max_iterations=2, max_retries=1, timeout_seconds=30),
            )
            store = LoopStore(db)
            store.initialize()
            store.create_job(job)
            store.close()

            reopened = LoopStore(db)
            reopened.initialize()
            self.assertEqual(reopened.get_job("persist-me"), job)

    def test_step_receipt_is_unique_for_same_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LoopStore(Path(tmp) / "state.loopfactory.db")
            store.initialize()
            store.record_step_receipt("job", 1, "demo/write", "abc", "def", "ev-1")
            with self.assertRaises(ValueError):
                store.record_step_receipt("job", 1, "demo/write", "abc", "def", "ev-2")
```

- [ ] **Step 2: Verify failure**

```bash
python -m unittest tests.loop_factory.test_store -v
```

Expected: import failure for `store`.

- [ ] **Step 3: Implement schema and transactional methods**

Create tables exactly:

```sql
CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY,
  manifest_json TEXT NOT NULL,
  state TEXT NOT NULL,
  attempt INTEGER NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS attempts (
  run_id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL,
  attempt_no INTEGER NOT NULL,
  parent_run_id TEXT,
  state TEXT NOT NULL,
  worker TEXT,
  lease_until TEXT,
  timestamp_start TEXT NOT NULL,
  timestamp_end TEXT,
  retry_count INTEGER NOT NULL DEFAULT 0,
  cost_eur REAL NOT NULL DEFAULT 0,
  error_class TEXT,
  next_exact_action TEXT,
  UNIQUE(job_id, attempt_no)
);
CREATE TABLE IF NOT EXISTS checkpoints (
  checkpoint_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  job_id TEXT NOT NULL,
  sequence INTEGER NOT NULL,
  payload_json TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(run_id, sequence)
);
CREATE TABLE IF NOT EXISTS step_receipts (
  job_id TEXT NOT NULL,
  attempt_no INTEGER NOT NULL,
  step_key TEXT NOT NULL,
  input_hash TEXT NOT NULL,
  output_hash TEXT NOT NULL,
  evidence_ref TEXT NOT NULL,
  completed_at TEXT NOT NULL,
  PRIMARY KEY(job_id, attempt_no, step_key, input_hash)
);
CREATE TABLE IF NOT EXISTS evidence (
  evidence_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  job_id TEXT NOT NULL,
  record_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
```

Use connection transactions (`with self._conn:`), parameterized SQL only, `PRAGMA foreign_keys=ON`, and `sqlite3.Row`. `append_checkpoint()` hashes the canonical JSON bytes (`sort_keys=True`, compact separators) before insert. `commit_step()` inserts receipt and checkpoint in the same transaction so a crash cannot leave a side effect marked complete without its durable checkpoint.

Update `.gitignore` with:

```text
.kai-loop/
*.loopfactory.db
*.loopfactory.db-*
```

- [ ] **Step 4: Run store tests**

```bash
python -m unittest tests.loop_factory.test_store -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/loop_factory/store.py tests/loop_factory/test_store.py .gitignore
git commit -m "feat(loop-factory): persist jobs and checkpoints in sqlite"
```

---

### Task 6: Structured Evidence and FREE-FIRST Capability Registry

**Files:**
- Create: `core/loop_factory/evidence.py`
- Create: `core/loop_factory/capabilities.py`
- Create: `tests/loop_factory/test_capabilities.py`

**Interfaces:**
- Produces: `EvidenceRecord`, `sha256_bytes()`, `sha256_text()`, `sha256_file()`.
- Produces: `Availability`, `CostClass`, `WorkerCapability`, `CapabilityRegistry`, `default_cell000_registry()`.
- `CapabilityRegistry.candidates(capability: str, max_cost_eur: float) -> list[WorkerCapability]` is deterministic.

- [ ] **Step 1: Write failing registry/evidence tests**

```python
# tests/loop_factory/test_capabilities.py
import unittest

from core.loop_factory.capabilities import Availability, CapabilityRegistry, CostClass, WorkerCapability, default_cell000_registry
from core.loop_factory.evidence import sha256_text


class CapabilityTests(unittest.TestCase):
    def test_free_first_ranking_is_deterministic(self):
        registry = CapabilityRegistry()
        registry.register(WorkerCapability("paid", frozenset({"python.test"}), "cloud", CostClass.PAID, Availability.AVAILABLE, 0.10))
        registry.register(WorkerCapability("local", frozenset({"python.test"}), "local", CostClass.LOCAL, Availability.AVAILABLE, 0.0))
        ids = [item.worker_id for item in registry.candidates("python.test", max_cost_eur=1.0)]
        self.assertEqual(ids, ["local", "paid"])

    def test_unverified_worker_is_not_selected_by_default(self):
        registry = default_cell000_registry()
        ids = [item.worker_id for item in registry.candidates("gpu.burst", max_cost_eur=100)]
        self.assertNotIn("hf-jobs", ids)

    def test_sha256_is_stable(self):
        self.assertEqual(sha256_text("kai"), sha256_text("kai"))
```

- [ ] **Step 2: Verify failure**

```bash
python -m unittest tests.loop_factory.test_capabilities -v
```

Expected: import failure.

- [ ] **Step 3: Implement registry and observability record**

`CostClass` ranking is exactly `LOCAL=0`, `OPEN=1`, `INCLUDED=2`, `PAID=3`. Filter candidates to `Availability.AVAILABLE` and `estimated_cost_eur <= max_cost_eur`, then sort by `(cost_class rank, estimated_cost_eur, worker_id)`.

`default_cell000_registry()` creates entries for `github-actions`, `termux`, `pc`, and `hf-jobs` but marks live machine/cloud entries `UNKNOWN`; capability probes in a later cell may replace availability. Do not persist the audit-time environment as eternal truth.

`EvidenceRecord` contains exactly the observability fields from the spec and serializes to/from a dict. It stores secret handles only; no secret-value field exists.

- [ ] **Step 4: Run tests**

```bash
python -m unittest tests.loop_factory.test_capabilities -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/loop_factory/evidence.py core/loop_factory/capabilities.py tests/loop_factory/test_capabilities.py
git commit -m "feat(loop-factory): add evidence and capability registry"
```

---

### Task 7: Deterministic Worker and One-Iteration Loop Runner

**Files:**
- Create: `core/loop_factory/workers.py`
- Create: `core/loop_factory/runner.py`
- Create: `tests/loop_factory/test_runner.py`

**Interfaces:**
- Produces: `StepContext`, `StepOutcome`, `Worker` protocol, `DemoFileWorker`.
- Produces: `RunResult`, `LoopRunner.run_once(job_id, *, branch, worker_id="demo-file", after_checkpoint=None) -> RunResult`.
- `after_checkpoint` is test/recovery dependency injection; production callers leave it `None`.

- [ ] **Step 1: Write failing idempotence, crash/resume, budget, and retry-ceiling tests**

```python
# tests/loop_factory/test_runner.py
import tempfile
import unittest
from pathlib import Path

from core.loop_factory.model import AutonomyLevel, Budget, JobManifest, JobState
from core.loop_factory.runner import LoopRunner
from core.loop_factory.store import LoopStore
from core.loop_factory.workers import DemoFileWorker


class LoopRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.sandbox = root / "sandbox"
        self.store = LoopStore(root / "state.loopfactory.db")
        self.store.initialize()
        self.job = JobManifest.new(
            job_id="demo",
            project="KAI_LOOP_FACTORY",
            cell_type="BUILD",
            goal="write deterministic marker",
            write_scope=[str(self.sandbox)],
            autonomy_level=AutonomyLevel.A2,
            allowed_tools=["demo-file"],
            budget=Budget(max_cost_eur=0, max_iterations=3, max_retries=1, timeout_seconds=30),
        )
        self.store.create_job(self.job)
        self.runner = LoopRunner(self.store, {"demo-file": DemoFileWorker(self.sandbox)})

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_run_succeeds_on_feature_branch(self):
        result = self.runner.run_once("demo", branch="feat/loop-factory-cell-000")
        self.assertEqual(result.state, JobState.SUCCEEDED)
        self.assertTrue((self.sandbox / "demo.txt").exists())

    def test_crash_after_checkpoint_resumes_without_repeating_side_effect(self):
        calls = {"count": 0}
        worker = DemoFileWorker(self.sandbox, on_write=lambda: calls.__setitem__("count", calls["count"] + 1))
        runner = LoopRunner(self.store, {"demo-file": worker})

        def crash():
            raise RuntimeError("simulated process death")

        with self.assertRaises(RuntimeError):
            runner.run_once("demo", branch="feat/loop-factory-cell-000", after_checkpoint=crash)
        self.assertEqual(calls["count"], 1)

        result = runner.run_once("demo", branch="feat/loop-factory-cell-000")
        self.assertEqual(result.state, JobState.SUCCEEDED)
        self.assertEqual(calls["count"], 1)
```

Add separate cases in the same file for canonical `main` rejection, zero-budget rejection of a synthetic costful worker, timeout/iteration/retry ceiling, expired lease recovery, and `UNKNOWN` -> `QUARANTINED` after the configured retry ceiling.

- [ ] **Step 2: Verify failure**

```bash
python -m unittest tests.loop_factory.test_runner -v
```

Expected: import failure for worker/runner modules.

- [ ] **Step 3: Implement the one-iteration engine**

`DemoFileWorker` writes `demo.txt` atomically using a temporary sibling followed by `Path.replace()`. Its payload is deterministic: `job_id`, `goal`, and input hash only. It reports cost `0.0` and output SHA-256.

`LoopRunner.run_once()` performs exactly:

```text
restore job/latest attempt/latest checkpoint
validate job limits and dependencies
policy + branch + write-scope preflight
create or recover attempt and lease
compute step_key + input_hash
if matching step_receipt exists: skip ACT
else ACT with one worker
atomically commit receipt + checkpoint
optional after_checkpoint hook
VERIFY output hash and required evidence
append evidence
mark attempt/job terminal or explicit REQUEUE
return state + run_id + evidence_ref + next_exact_action
```

Generate IDs with `uuid.uuid4().hex`. Lease timestamps use UTC. A stale `RUNNING` attempt is recoverable only after `lease_until`; it is never interpreted as success. Catch `LoopFactoryError` separately from arbitrary exceptions. Arbitrary exceptions map to `ErrorClass.UNKNOWN`; retry while below the job ceiling, otherwise `QUARANTINED`. Do not contain a `while True` loop.

A BUILD success must have at least one verification evidence record before `SUCCEEDED`.

- [ ] **Step 4: Run runner tests twice to prove deterministic replay**

```bash
python -m unittest tests.loop_factory.test_runner -v
python -m unittest tests.loop_factory.test_runner -v
```

Expected: both PASS.

- [ ] **Step 5: Commit**

```bash
git add core/loop_factory/workers.py core/loop_factory/runner.py tests/loop_factory/test_runner.py
git commit -m "feat(loop-factory): execute restart-safe single iterations"
```

---

### Task 8: Drive-Ready Writeback Renderer and CLI

**Files:**
- Create: `core/loop_factory/writeback.py`
- Create: `core/loop_factory/cli.py`
- Create: `core/loop_factory/__main__.py`
- Create: `tests/loop_factory/test_cli.py`

**Interfaces:**
- Produces: `build_drive_checkpoint_payload(...) -> dict[str, object]`, `render_drive_checkpoint_markdown(...) -> str`.
- CLI commands: `init`, `create`, `show`, `run-once`, `checkpoint`, `requeue`, `cancel`, `workers`.

- [ ] **Step 1: Write failing CLI/writeback tests**

```python
# tests/loop_factory/test_cli.py
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from core.loop_factory.cli import main
from core.loop_factory.writeback import render_drive_checkpoint_markdown


class CliTests(unittest.TestCase):
    def test_init_creates_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "state.loopfactory.db"
            code = main(["init", "--db", str(db)])
            self.assertEqual(code, 0)
            self.assertTrue(db.exists())

    def test_workers_output_is_json(self):
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = main(["workers"])
        self.assertEqual(code, 0)
        self.assertIsInstance(json.loads(stream.getvalue()), list)

    def test_checkpoint_markdown_contains_exact_next_action(self):
        text = render_drive_checkpoint_markdown({"job_id": "demo", "next_exact_action": "review evidence"})
        self.assertIn("demo", text)
        self.assertIn("review evidence", text)
```

- [ ] **Step 2: Verify failure**

```bash
python -m unittest tests.loop_factory.test_cli -v
```

Expected: import failure.

- [ ] **Step 3: Implement CLI with machine-readable output**

`python -m core.loop_factory` delegates to `cli.main(sys.argv[1:])`. Every command except `checkpoint --format markdown` prints one JSON document to stdout. Operational failures print one JSON error document to stderr and return nonzero.

Required invocations:

```bash
python -m core.loop_factory init --db .kai-loop/loopfactory.db
python -m core.loop_factory create --db .kai-loop/loopfactory.db --manifest job.json
python -m core.loop_factory show --db .kai-loop/loopfactory.db CELL-000-DEMO
python -m core.loop_factory run-once --db .kai-loop/loopfactory.db CELL-000-DEMO --sandbox .kai-loop/sandboxes/CELL-000-DEMO --branch feat/loop-factory-cell-000
python -m core.loop_factory checkpoint --db .kai-loop/loopfactory.db CELL-000-DEMO --format markdown
python -m core.loop_factory requeue --db .kai-loop/loopfactory.db CELL-000-DEMO --reason "retry after environment repair"
python -m core.loop_factory cancel --db .kai-loop/loopfactory.db CELL-000-DEMO --reason "operator cancelled"
python -m core.loop_factory workers
```

If `--branch` is omitted for `run-once`, call `detect_git_branch(Path.cwd())`; never default to `main`.

`build_drive_checkpoint_payload()` returns plain JSON-compatible values and includes state, latest run/evidence refs, hashes, error class, and `next_exact_action`. It performs no network call and imports no Drive SDK.

- [ ] **Step 4: Run CLI tests and one manual help smoke**

```bash
python -m unittest tests.loop_factory.test_cli -v
python -m core.loop_factory --help
```

Expected: tests PASS and help exits 0.

- [ ] **Step 5: Commit**

```bash
git add core/loop_factory/writeback.py core/loop_factory/cli.py core/loop_factory/__main__.py tests/loop_factory/test_cli.py
git commit -m "feat(loop-factory): expose governed CLI and checkpoint writeback"
```

---

### Task 9: CELL-000 End-to-End Acceptance Test and CI

**Files:**
- Create: `tests/loop_factory/test_cell000_acceptance.py`
- Create: `.github/workflows/test-loop-factory.yml`

**Interfaces:**
- Acceptance test is the executable definition of CELL-000 completion criteria.
- CI becomes the promotion evidence source for later PR review.

- [ ] **Step 1: Write the acceptance test before altering CI**

```python
# tests/loop_factory/test_cell000_acceptance.py
import tempfile
import unittest
from pathlib import Path

from core.loop_factory.model import AutonomyLevel, Budget, JobManifest, JobState
from core.loop_factory.runner import LoopRunner
from core.loop_factory.store import LoopStore
from core.loop_factory.writeback import build_drive_checkpoint_payload
from core.loop_factory.workers import DemoFileWorker


class Cell000AcceptanceTests(unittest.TestCase):
    def test_fresh_state_survives_checkpoint_crash_and_resumes_idempotently(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "state.loopfactory.db"
            sandbox = root / "sandbox"
            store = LoopStore(db)
            store.initialize()
            job = JobManifest.new(
                job_id="CELL-000-ACCEPTANCE",
                project="KAI_LOOP_FACTORY",
                cell_type="BUILD",
                goal="prove durable autonomy substrate",
                write_scope=[str(sandbox)],
                autonomy_level=AutonomyLevel.A2,
                allowed_tools=["demo-file"],
                budget=Budget(max_cost_eur=0, max_iterations=3, max_retries=1, timeout_seconds=30),
            )
            store.create_job(job)
            writes = {"count": 0}
            worker = DemoFileWorker(sandbox, on_write=lambda: writes.__setitem__("count", writes["count"] + 1))
            runner = LoopRunner(store, {"demo-file": worker})

            with self.assertRaises(RuntimeError):
                runner.run_once(
                    job.job_id,
                    branch="feat/loop-factory-cell-000",
                    after_checkpoint=lambda: (_ for _ in ()).throw(RuntimeError("kill after checkpoint")),
                )
            store.close()

            reopened = LoopStore(db)
            reopened.initialize()
            resumed = LoopRunner(reopened, {"demo-file": worker}).run_once(
                job.job_id,
                branch="feat/loop-factory-cell-000",
            )
            self.assertEqual(resumed.state, JobState.SUCCEEDED)
            self.assertEqual(writes["count"], 1)
            payload = build_drive_checkpoint_payload(reopened.get_job(job.job_id), reopened.get_latest_attempt(job.job_id), reopened.list_evidence(job.job_id))
            self.assertEqual(payload["job_id"], job.job_id)
            self.assertTrue(payload["next_exact_action"])
```

Add explicit acceptance methods for: `main` rejection before mutation, out-of-scope rejection, retry ceiling, budget ceiling, evidence presence, and CLI create/show/checkpoint path. Each method maps to one or more of the 12 spec completion criteria.

- [ ] **Step 2: Run the complete suite before adding workflow**

```bash
python -m compileall -q core/loop_factory
python -m unittest discover -s tests/loop_factory -p 'test_*.py' -v
```

Expected: PASS. If a spec criterion lacks an assertion, add that assertion before proceeding.

- [ ] **Step 3: Add GitHub-hosted CI**

Create `.github/workflows/test-loop-factory.yml`:

```yaml
name: Test Loop Factory

on:
  pull_request:
    paths:
      - 'core/loop_factory/**'
      - 'tests/loop_factory/**'
      - 'docs/loop_factory/**'
      - 'docs/superpowers/specs/2026-09-16-autonomy-foundation-design.md'
      - 'docs/superpowers/plans/2026-09-16-autonomy-foundation.md'
      - '.github/workflows/test-loop-factory.yml'
      - '.gitignore'
  push:
    branches:
      - 'feat/loop-factory-cell-000'
    paths:
      - 'core/loop_factory/**'
      - 'tests/loop_factory/**'
      - '.github/workflows/test-loop-factory.yml'

permissions:
  contents: read

jobs:
  unittest:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ['3.11', '3.12']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Compile Loop Factory
        run: python -m compileall -q core/loop_factory
      - name: Run CELL-000 tests
        run: python -m unittest discover -s tests/loop_factory -p 'test_*.py' -v
```

- [ ] **Step 4: Run local equivalent one final time**

```bash
python -m compileall -q core/loop_factory
python -m unittest discover -s tests/loop_factory -p 'test_*.py' -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/loop_factory/test_cell000_acceptance.py .github/workflows/test-loop-factory.yml
git commit -m "test(loop-factory): gate CELL-000 with end-to-end acceptance"
```

---

### Task 10: Runbook, Isolated Implementation Branch, Review, and Promotion Evidence

**Files:**
- Create: `docs/loop_factory/CELL_000_RUNBOOK.md`
- Verify only: `docs/superpowers/specs/2026-09-16-autonomy-foundation-design.md`
- Verify only: `docs/superpowers/plans/2026-09-16-autonomy-foundation.md`

**Interfaces:**
- Runbook documents human recovery and exact commands; it does not become executable policy.
- Promotion remains a separate reviewed action; this task does not merge to `main`.

- [ ] **Step 1: Write the runbook from verified commands only**

The runbook must include these exact sections and commands:

```markdown
# CELL-000 Runbook

## Authorities
- GitHub: live code and commits.
- SQLite: runtime job/attempt/checkpoint/evidence state.
- Drive: documentary CURRENT/checkpoint writeback only.

## Fresh start
python -m core.loop_factory init --db .kai-loop/loopfactory.db

## Focused verification
python -m compileall -q core/loop_factory
python -m unittest discover -s tests/loop_factory -p 'test_*.py' -v

## Branch safety
Never run a mutating cell on `main` or `master`.

## Crash recovery
1. Re-open the same SQLite DB.
2. Inspect the job with `show`.
3. Inspect checkpoint output.
4. Run exactly one `run-once` iteration.
5. Verify the existing step receipt prevents duplicate side effects.

## Promotion gate
Promotion requires fresh CI evidence, reviewed diff, expected head SHA, rollback path, and explicit A4 approval.
```

Also document the known CELL-000 limits: no distributed lock service, no live provider probes, no UI, no automatic Drive write, no automatic merge, no background daemon.

- [ ] **Step 2: Run self-audit commands and inspect Git diff**

```bash
python -m compileall -q core/loop_factory
python -m unittest discover -s tests/loop_factory -p 'test_*.py' -v
git status --short
git diff --check
git diff --stat docs/autonomy-foundation-20260916...HEAD
```

Expected: tests PASS, `git diff --check` emits nothing, and the diff is limited to CELL-000 files plus the approved spec/plan lineage.

- [ ] **Step 3: Commit the runbook**

```bash
git add docs/loop_factory/CELL_000_RUNBOOK.md
git commit -m "docs(loop-factory): add CELL-000 recovery runbook"
```

- [ ] **Step 4: Push implementation branch and open a draft PR only**

The implementation branch must be created from the approved design branch head so the spec and plan travel with the code:

```bash
git switch docs/autonomy-foundation-20260916
git pull --ff-only
git switch -c feat/loop-factory-cell-000
git push -u origin feat/loop-factory-cell-000
```

Open a **draft** PR from `feat/loop-factory-cell-000` to `main`. Do not mark ready and do not enable auto-merge in this task.

PR body must record:
- spec path;
- plan path;
- focused test command and result count;
- CI run URL/ID when available;
- head SHA;
- explicit statement that direct canonical writes are guarded;
- rollback = close PR / delete candidate branch after preserving evidence.

- [ ] **Step 5: Independent review gate**

Review specifically for:
- direct or implicit writes to `main`/`master`;
- path traversal/symlink escape in write-scope checks;
- SQLite transaction gaps around receipt/checkpoint;
- retry loops without ceilings;
- secrets in serialized/logged structures;
- attempts being mutated instead of superseded;
- evidence missing before BUILD success;
- false assumptions about PC/Termux/HF availability;
- CI using only GitHub-hosted runners.

Any finding is fixed on the feature branch, followed by the full test suite and a new commit. Do not merge in the same operation as review.

- [ ] **Step 6: Documentary writeback after verified implementation**

After tests and review pass, render the Drive-ready checkpoint with:

```bash
python -m core.loop_factory checkpoint --db .kai-loop/loopfactory.db CELL-000-ACCEPTANCE --format markdown
```

Use the resulting payload to update the affected Drive CURRENT/checkpoint through the authorized Drive connector. The code itself must remain functional if that external writeback is skipped or temporarily unavailable.

- [ ] **Step 7: Final implementation commit check**

```bash
git log --oneline --decorate -12
git status --short
```

Expected: clean working tree and a sequence of small CELL-000 commits. Promotion to `main` is a separate A4 action after human review/approval and fresh expected-head verification.

---

## Plan-to-Spec Coverage Matrix

| Spec requirement | Implemented by |
|---|---|
| Typed job/state schema + serialization | Task 1 |
| Error taxonomy | Tasks 1, 7 |
| Deterministic state transitions | Task 2 |
| Canonical branch/write-scope guard | Task 3 |
| Autonomy/budget/security policy | Task 4 |
| SQLite jobs/attempts/checkpoints | Task 5 |
| Atomic step receipt + checkpoint | Task 5 |
| Structured evidence | Task 6 |
| FREE-FIRST capability registry | Task 6 |
| One-iteration bounded runner | Task 7 |
| Restart/resume and idempotency | Tasks 5, 7, 9 |
| Lease/expired-run recovery | Task 7 |
| Retry/budget/iteration/timeout ceilings | Tasks 4, 7, 9 |
| CLI create/show/run-once/checkpoint/requeue/cancel | Task 8 |
| Drive-ready writeback without Drive dependency | Tasks 8, 9, 10 |
| Fresh-clone acceptance gate | Task 9 |
| GitHub-hosted CI | Task 9 |
| Human recovery/runbook | Task 10 |
| Separate promotion gate | Tasks 4, 10 |

## Execution Boundary

This plan stops at a reviewed **draft PR** and evidence-ready checkpoint. It does not merge to `main`, enable auto-merge, change repository protection settings, provision paid compute, rotate credentials, install a self-hosted GitHub runner, or start a long-running daemon. Those are separate governed actions.
