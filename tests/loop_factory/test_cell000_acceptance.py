import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from core.loop_factory.cli import main
from core.loop_factory.errors import LoopFactoryError
from core.loop_factory.model import AutonomyLevel, Budget, ErrorClass, JobManifest, JobState
from core.loop_factory.runner import LoopRunner
from core.loop_factory.store import LoopStore
from core.loop_factory.workers import DemoFileWorker
from core.loop_factory.writeback import build_drive_checkpoint_payload


BRANCH = "feat/loop-factory-cell-000"


class Cell000AcceptanceTests(unittest.TestCase):
    def make_job(self, root: Path, job_id: str = "CELL-000-ACCEPTANCE", **budget):
        limits = dict(max_cost_eur=0, max_iterations=3, max_retries=1, timeout_seconds=30)
        limits.update(budget)
        return JobManifest.new(
            job_id=job_id,
            project="KAI_LOOP_FACTORY",
            cell_type="BUILD",
            goal="prove durable autonomy substrate",
            write_scope=[str(root / "sandbox")],
            autonomy_level=AutonomyLevel.A2,
            allowed_tools=["demo-file"],
            budget=Budget(**limits),
        )

    def test_01_fresh_manifest_can_be_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            job = self.make_job(Path(tmp))
            self.assertEqual(job.state, JobState.QUEUED)
            self.assertEqual(JobManifest.from_json(job.to_json()), job)

    def test_02_manifest_persists_to_sqlite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "state.loopfactory.db"
            store = LoopStore(db); store.initialize()
            job = self.make_job(root); store.create_job(job); store.close()
            reopened = LoopStore(db); reopened.initialize()
            self.assertEqual(reopened.get_job(job.job_id), job)
            reopened.close()

    def test_03_deterministic_demo_executes_in_feature_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); sandbox = root / "sandbox"
            store = LoopStore(root / "state.loopfactory.db"); store.initialize()
            job = self.make_job(root); store.create_job(job)
            result = LoopRunner(store, {"demo-file": DemoFileWorker(sandbox)}).run_once(
                job.job_id, branch=BRANCH)
            self.assertEqual(result.state, JobState.SUCCEEDED)
            first = (sandbox / "demo.txt").read_bytes()
            self.assertTrue(first)
            store.close()

    def test_04_material_step_creates_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); store = LoopStore(root / "state.loopfactory.db"); store.initialize()
            job = self.make_job(root); store.create_job(job)
            LoopRunner(store, {"demo-file": DemoFileWorker(root / "sandbox")}).run_once(
                job.job_id, branch=BRANCH)
            checkpoint = store.latest_checkpoint(job.job_id)
            self.assertIsNotNone(checkpoint)
            self.assertEqual(checkpoint["phase"], JobState.CHECKPOINTED.value)
            store.close()

    def test_05_forced_crash_after_checkpoint_survives_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); db = root / "state.loopfactory.db"; sandbox = root / "sandbox"
            store = LoopStore(db); store.initialize(); job = self.make_job(root); store.create_job(job)
            writes = {"count": 0}
            worker = DemoFileWorker(sandbox, on_write=lambda: writes.__setitem__("count", writes["count"] + 1))
            with self.assertRaises(RuntimeError):
                LoopRunner(store, {"demo-file": worker}).run_once(
                    job.job_id, branch=BRANCH,
                    after_checkpoint=lambda: (_ for _ in ()).throw(RuntimeError("forced death")))
            store.close()
            reopened = LoopStore(db); reopened.initialize()
            self.assertIsNotNone(reopened.latest_checkpoint(job.job_id))
            result = LoopRunner(reopened, {"demo-file": worker}).run_once(job.job_id, branch=BRANCH)
            self.assertEqual(result.state, JobState.SUCCEEDED)
            self.assertEqual(writes["count"], 1)
            reopened.close()

    def test_06_receipt_prevents_duplicate_committed_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); db = root / "state.loopfactory.db"; sandbox = root / "sandbox"
            store = LoopStore(db); store.initialize(); job = self.make_job(root); store.create_job(job)
            writes = {"count": 0}
            worker = DemoFileWorker(sandbox, on_write=lambda: writes.__setitem__("count", writes["count"] + 1))
            runner = LoopRunner(store, {"demo-file": worker})
            with self.assertRaises(RuntimeError):
                runner.run_once(job.job_id, branch=BRANCH,
                    after_checkpoint=lambda: (_ for _ in ()).throw(RuntimeError("stop")))
            runner.run_once(job.job_id, branch=BRANCH)
            runner.run_once(job.job_id, branch=BRANCH)
            self.assertEqual(writes["count"], 1)
            store.close()

    def test_07_main_write_is_refused_before_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); sandbox = root / "sandbox"
            store = LoopStore(root / "state.loopfactory.db"); store.initialize()
            job = self.make_job(root); store.create_job(job)
            with self.assertRaises(LoopFactoryError) as ctx:
                LoopRunner(store, {"demo-file": DemoFileWorker(sandbox)}).run_once(job.job_id, branch="main")
            self.assertEqual(ctx.exception.error_class, ErrorClass.CANONICAL_BRANCH_GUARD)
            self.assertFalse((sandbox / "demo.txt").exists())
            store.close()

    def test_08_out_of_scope_write_is_refused_before_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); outside = root / "outside"
            store = LoopStore(root / "state.loopfactory.db"); store.initialize()
            job = self.make_job(root); store.create_job(job)
            with self.assertRaises(LoopFactoryError) as ctx:
                LoopRunner(store, {"demo-file": DemoFileWorker(outside)}).run_once(job.job_id, branch=BRANCH)
            self.assertEqual(ctx.exception.error_class, ErrorClass.WRITE_SCOPE_VIOLATION)
            self.assertFalse((outside / "demo.txt").exists())
            store.close()

    def test_09_retry_and_budget_ceilings_stop_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); store = LoopStore(root / "state.loopfactory.db"); store.initialize()
            job = self.make_job(root, max_retries=0); store.create_job(job)
            class Boom:
                worker_id = "demo-file"; sandbox = root / "sandbox"; estimated_cost_eur = 0.0
                def run(self, context): raise RuntimeError("boom")
            result = LoopRunner(store, {"demo-file": Boom()}).run_once(job.job_id, branch=BRANCH)
            self.assertEqual(result.state, JobState.QUARANTINED)
            store.close()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); store = LoopStore(root / "state.loopfactory.db"); store.initialize()
            job = self.make_job(root, max_cost_eur=0); store.create_job(job)
            class Costly:
                worker_id = "demo-file"; sandbox = root / "sandbox"; estimated_cost_eur = 0.01
                def run(self, context): raise AssertionError("must not run")
            with self.assertRaises(LoopFactoryError) as ctx:
                LoopRunner(store, {"demo-file": Costly()}).run_once(job.job_id, branch=BRANCH)
            self.assertEqual(ctx.exception.error_class, ErrorClass.BUDGET_EXCEEDED)
            store.close()

    def test_10_structured_evidence_has_exact_next_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); store = LoopStore(root / "state.loopfactory.db"); store.initialize()
            job = self.make_job(root); store.create_job(job)
            result = LoopRunner(store, {"demo-file": DemoFileWorker(root / "sandbox")}).run_once(
                job.job_id, branch=BRANCH)
            evidence = store.list_evidence(job.job_id)
            self.assertEqual(len(evidence), 1)
            self.assertEqual(evidence[0].result_state, JobState.SUCCEEDED)
            self.assertEqual(evidence[0].next_exact_action, result.next_exact_action)
            self.assertTrue(result.next_exact_action)
            store.close()

    def test_11_cli_create_show_checkpoint_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); db = root / "state.loopfactory.db"; manifest = root / "job.json"
            manifest.write_text(self.make_job(root, "cli-acceptance").to_json(), encoding="utf-8")
            self.assertEqual(main(["init", "--db", str(db)]), 0)
            self.assertEqual(main(["create", "--db", str(db), "--manifest", str(manifest)]), 0)
            stream = io.StringIO()
            with redirect_stdout(stream):
                self.assertEqual(main(["show", "--db", str(db), "cli-acceptance"]), 0)
            self.assertEqual(json.loads(stream.getvalue())["job_id"], "cli-acceptance")
            stream = io.StringIO()
            with redirect_stdout(stream):
                self.assertEqual(main(["checkpoint", "--db", str(db), "cli-acceptance"]), 0)
            self.assertEqual(json.loads(stream.getvalue())["job_id"], "cli-acceptance")

    def test_12_drive_ready_payload_needs_no_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); store = LoopStore(root / "state.loopfactory.db"); store.initialize()
            job = self.make_job(root); store.create_job(job)
            payload = build_drive_checkpoint_payload(job, None, [])
            self.assertEqual(payload["job_id"], job.job_id)
            self.assertTrue(payload["next_exact_action"])
            json.dumps(payload)
            store.close()

    def test_13_ci_workflow_runs_regression_suite_on_hosted_runner(self):
        workflow = Path(".github/workflows/test-loop-factory.yml")
        self.assertTrue(workflow.exists())
        text = workflow.read_text(encoding="utf-8")
        self.assertIn("runs-on: ubuntu-latest", text)
        self.assertIn("python -m unittest discover", text)
        self.assertIn("permissions:\n  contents: read", text)
