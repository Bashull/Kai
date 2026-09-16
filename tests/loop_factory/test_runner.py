import tempfile
import time
import unittest
from pathlib import Path

from core.loop_factory.errors import LoopFactoryError
from core.loop_factory.model import AutonomyLevel, Budget, ErrorClass, JobManifest, JobState
from core.loop_factory.runner import LoopRunner
from core.loop_factory.store import LoopStore
from core.loop_factory.workers import DemoFileWorker, StepOutcome


class LoopRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.sandbox = self.root / "sandbox"
        self.store = LoopStore(self.root / "state.loopfactory.db")
        self.store.initialize()
        self.create_job()

    def create_job(self, **budget_overrides):
        defaults = dict(max_cost_eur=0, max_iterations=3, max_retries=1, timeout_seconds=30)
        defaults.update(budget_overrides)
        job = JobManifest.new(
            job_id="demo", project="KAI_LOOP_FACTORY", cell_type="BUILD",
            goal="write deterministic marker", write_scope=[str(self.sandbox)],
            autonomy_level=AutonomyLevel.A2, allowed_tools=["demo-file"],
            budget=Budget(**defaults),
        )
        self.store.create_job(job)
        return job

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_run_succeeds_on_feature_branch(self):
        runner = LoopRunner(self.store, {"demo-file": DemoFileWorker(self.sandbox)})
        result = runner.run_once("demo", branch="feat/loop-factory-cell-000")
        self.assertEqual(result.state, JobState.SUCCEEDED)
        self.assertTrue((self.sandbox / "demo.txt").exists())
        self.assertEqual(len(self.store.list_evidence("demo")), 1)

    def test_crash_after_checkpoint_resumes_without_duplicate_write(self):
        calls = {"count": 0}
        worker = DemoFileWorker(
            self.sandbox,
            on_write=lambda: calls.__setitem__("count", calls["count"] + 1),
        )
        runner = LoopRunner(self.store, {"demo-file": worker})

        def crash():
            raise RuntimeError("simulated process death")

        with self.assertRaises(RuntimeError):
            runner.run_once("demo", branch="feat/loop-factory-cell-000", after_checkpoint=crash)
        self.assertEqual(calls["count"], 1)
        result = runner.run_once("demo", branch="feat/loop-factory-cell-000")
        self.assertEqual(result.state, JobState.SUCCEEDED)
        self.assertEqual(calls["count"], 1)

    def test_main_branch_is_rejected_before_write(self):
        runner = LoopRunner(self.store, {"demo-file": DemoFileWorker(self.sandbox)})
        with self.assertRaises(LoopFactoryError) as ctx:
            runner.run_once("demo", branch="main")
        self.assertEqual(ctx.exception.error_class, ErrorClass.CANONICAL_BRANCH_GUARD)
        self.assertFalse((self.sandbox / "demo.txt").exists())

    def test_unknown_failure_quarantines_at_retry_ceiling(self):
        class BoomWorker:
            worker_id = "demo-file"
            sandbox = self.sandbox
            estimated_cost_eur = 0.0

            def run(self, context):
                raise RuntimeError("boom")

        self.store.close()
        self.tmp.cleanup()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.sandbox = self.root / "sandbox"
        self.store = LoopStore(self.root / "state.loopfactory.db")
        self.store.initialize()
        self.create_job(max_retries=0)
        BoomWorker.sandbox = self.sandbox
        result = LoopRunner(self.store, {"demo-file": BoomWorker()}).run_once(
            "demo", branch="feat/loop-factory-cell-000"
        )
        self.assertEqual(result.state, JobState.QUARANTINED)
        self.assertEqual(self.store.get_job("demo").last_error_class, ErrorClass.UNKNOWN)

    def test_timeout_overrun_cannot_succeed(self):
        class SlowWorker:
            worker_id = "demo-file"
            sandbox = self.sandbox
            estimated_cost_eur = 0.0

            def run(self, context):
                time.sleep(0.02)
                return StepOutcome("out", "slow", verified=True)

        job = self.store.get_job("demo")
        job.budget.timeout_seconds = 0
        self.store.update_job(job)
        SlowWorker.sandbox = self.sandbox
        result = LoopRunner(self.store, {"demo-file": SlowWorker()}).run_once(
            "demo", branch="feat/loop-factory-cell-000"
        )
        self.assertNotEqual(result.state, JobState.SUCCEEDED)

    def test_out_of_scope_worker_is_rejected_before_write(self):
        outside = self.root / "outside"
        runner = LoopRunner(self.store, {"demo-file": DemoFileWorker(outside)})
        with self.assertRaises(LoopFactoryError) as ctx:
            runner.run_once("demo", branch="feat/loop-factory-cell-000")
        self.assertEqual(ctx.exception.error_class, ErrorClass.WRITE_SCOPE_VIOLATION)
        self.assertFalse((outside / "demo.txt").exists())

    def test_estimated_cost_above_budget_is_rejected_before_attempt(self):
        class CostlyWorker:
            worker_id = "demo-file"
            sandbox = self.sandbox
            estimated_cost_eur = 0.01
            def run(self, context):
                raise AssertionError("must not run")

        CostlyWorker.sandbox = self.sandbox
        runner = LoopRunner(self.store, {"demo-file": CostlyWorker()})
        with self.assertRaises(LoopFactoryError) as ctx:
            runner.run_once("demo", branch="feat/loop-factory-cell-000")
        self.assertEqual(ctx.exception.error_class, ErrorClass.BUDGET_EXCEEDED)
        self.assertIsNone(self.store.get_latest_attempt("demo"))

    def test_retry_creates_fresh_attempt_and_can_succeed(self):
        calls = {"count": 0}
        class FlakyWorker:
            worker_id = "demo-file"
            sandbox = self.sandbox
            estimated_cost_eur = 0.0
            def run(self, context):
                calls["count"] += 1
                if calls["count"] == 1:
                    raise RuntimeError("first attempt fails")
                return StepOutcome("stable-output", "recovered", verified=True)

        FlakyWorker.sandbox = self.sandbox
        runner = LoopRunner(self.store, {"demo-file": FlakyWorker()})
        first = runner.run_once("demo", branch="feat/loop-factory-cell-000")
        self.assertEqual(first.state, JobState.REQUEUE)
        second = runner.run_once("demo", branch="feat/loop-factory-cell-000")
        self.assertEqual(second.state, JobState.SUCCEEDED)
        self.assertEqual(calls["count"], 2)
        self.assertEqual(self.store.get_latest_attempt("demo").attempt_no, 2)

    def test_iteration_ceiling_prevents_another_attempt(self):
        job = self.store.get_job("demo")
        job.budget.max_iterations = 1
        job.budget.max_retries = 1
        self.store.update_job(job)
        class AlwaysFail:
            worker_id = "demo-file"
            sandbox = self.sandbox
            estimated_cost_eur = 0.0
            def run(self, context):
                raise RuntimeError("nope")

        AlwaysFail.sandbox = self.sandbox
        runner = LoopRunner(self.store, {"demo-file": AlwaysFail()})
        self.assertEqual(
            runner.run_once("demo", branch="feat/loop-factory-cell-000").state,
            JobState.REQUEUE,
        )
        second = runner.run_once("demo", branch="feat/loop-factory-cell-000")
        self.assertEqual(second.state, JobState.QUARANTINED)
        self.assertEqual(self.store.get_latest_attempt("demo").attempt_no, 1)

    def test_expired_running_lease_is_recovered(self):
        attempt = self.store.start_attempt("demo", "demo-file")
        self.store.mark_attempt_state(attempt.run_id, JobState.RUNNING)
        self.store.heartbeat(attempt.run_id, "2000-01-01T00:00:00Z")
        runner = LoopRunner(self.store, {"demo-file": DemoFileWorker(self.sandbox)})
        result = runner.run_once("demo", branch="feat/loop-factory-cell-000")
        self.assertEqual(result.state, JobState.SUCCEEDED)
        self.assertEqual(self.store.get_latest_attempt("demo").attempt_no, 1)
