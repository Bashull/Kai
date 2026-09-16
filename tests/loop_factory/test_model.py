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

    def test_recursive_secret_key_is_rejected(self):
        payload = self.make_job().to_dict()
        payload["metadata"] = {"api_key": "sk-not-allowed"}
        with self.assertRaises(ValueError):
            JobManifest.from_dict(payload)

    def test_serialized_manifest_is_valid_json(self):
        parsed = json.loads(self.make_job().to_json())
        self.assertEqual(parsed["schema_version"], 1)
