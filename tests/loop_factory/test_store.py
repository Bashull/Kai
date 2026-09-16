import tempfile
import unittest
from pathlib import Path

from core.loop_factory.model import AutonomyLevel, Budget, JobManifest, JobState
from core.loop_factory.store import LoopStore


class LoopStoreTests(unittest.TestCase):
    def make_job(self, root: Path, job_id: str = "persist-me") -> JobManifest:
        return JobManifest.new(
            job_id=job_id,
            project="KAI_LOOP_FACTORY",
            cell_type="BUILD",
            goal="persist",
            write_scope=[str(root / "sandbox")],
            autonomy_level=AutonomyLevel.A2,
            allowed_tools=["demo-file"],
            budget=Budget(max_cost_eur=0, max_iterations=2, max_retries=1, timeout_seconds=30),
        )

    def test_job_survives_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "state.loopfactory.db"
            job = self.make_job(root)
            store = LoopStore(db)
            store.initialize()
            store.create_job(job)
            store.close()
            reopened = LoopStore(db)
            reopened.initialize()
            self.assertEqual(reopened.get_job("persist-me"), job)
            reopened.close()

    def test_duplicate_step_receipt_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LoopStore(Path(tmp) / "state.loopfactory.db")
            store.initialize()
            store.record_step_receipt("job", 1, "demo/write", "abc", "def", "ev-1")
            with self.assertRaises(ValueError):
                store.record_step_receipt("job", 1, "demo/write", "abc", "def", "ev-2")
            store.close()

    def test_commit_step_persists_receipt_and_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = LoopStore(root / "state.loopfactory.db")
            store.initialize()
            job = self.make_job(root, "atomic")
            store.create_job(job)
            attempt = store.start_attempt(job.job_id, "demo-file")
            store.mark_attempt_state(attempt.run_id, JobState.RUNNING)
            checkpoint_id = store.commit_step(
                attempt.run_id, job.job_id, attempt.attempt_no,
                "demo/write", "abc", "def", "ev-1", {"phase": "CHECKPOINTED"},
            )
            self.assertTrue(checkpoint_id)
            receipt = store.find_step_receipt(job.job_id, attempt.attempt_no, "demo/write", "abc")
            self.assertEqual(receipt["output_hash"], "def")
            self.assertEqual(store.latest_checkpoint(job.job_id)["phase"], "CHECKPOINTED")
            store.close()

    def test_terminal_attempt_cannot_be_reopened(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = LoopStore(root / "state.loopfactory.db")
            store.initialize()
            job = self.make_job(root, "terminal")
            store.create_job(job)
            attempt = store.start_attempt(job.job_id, "demo-file")
            store.mark_attempt_state(attempt.run_id, JobState.RUNNING)
            store.mark_attempt_state(attempt.run_id, JobState.FAILED)
            with self.assertRaises(ValueError):
                store.mark_attempt_state(attempt.run_id, JobState.RUNNING)
            store.close()
