import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from audio_studio.execution import ExecutionBlocked, ExecutionPolicy, authorize_execution, require_execution_authorization
from audio_studio.ingestion import OutputIngestionError, OutputIngestor
from audio_studio.models import Availability, CapabilitySnapshot


def snapshot(cost_class="UNKNOWN", availability=Availability.AVAILABLE):
    return CapabilitySnapshot(provider_id="ace-step-1.5-cloud", availability=availability, capabilities=frozenset({"text_to_music"}), cost_class=cost_class, runtime="REMOTE")


class ExecutionGateTests(unittest.TestCase):
    def test_unknown_cost_is_blocked_by_default(self):
        receipt = authorize_execution(snapshot())
        self.assertFalse(receipt.allowed)
        self.assertEqual(receipt.reason, "UNKNOWN_COST_BLOCKED")
        self.assertNotIn("approved_by", receipt.policy)

    def test_free_route_is_allowed_without_spending_approval(self):
        receipt = authorize_execution(snapshot("FREE"), now="2026-08-27T00:00:00Z")
        self.assertTrue(receipt.allowed)
        self.assertIsNone(receipt.estimated_cost_usd)

    def test_paid_route_requires_approval_and_budget(self):
        policy = ExecutionPolicy(free_only=False, max_cost_usd=Decimal("0.25"), approved_by="Asier", approved_at="2026-08-27T00:00:00Z")
        self.assertTrue(authorize_execution(snapshot("PAID"), policy, estimated_cost_usd="0.20").allowed)
        with self.assertRaisesRegex(ExecutionBlocked, "BUDGET_EXCEEDED"):
            require_execution_authorization(snapshot("PAID"), policy, estimated_cost_usd="0.30")


class OutputIngestorTests(unittest.TestCase):
    def manifest(self):
        return {"schema_version": "1.0.0", "case_id": "case-1", "status": "READY", "blueprint": {}, "provider": {}, "generation": {}, "assets": [], "evidence": {}}

    def test_ingests_by_reference_with_hash_and_no_move(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); bench, outputs = root / "bench", root / "outputs"
            bench.mkdir(); outputs.mkdir()
            manifest = bench / "manifest.json"; manifest.write_text(json.dumps(self.manifest()), encoding="utf-8")
            audio = outputs / "song.mp3"; audio.write_bytes(b"not-real-audio")
            result = OutputIngestor(bench, outputs).ingest(manifest, [audio], {"model": "acemusic/acestep-v1.5-turbo"}, provider_id="ace-step-1.5-cloud", ingested_at="2026-08-27T00:00:00Z")
            self.assertTrue(audio.exists())
            self.assertEqual(result["status"], "GENERATED")
            self.assertEqual(result["assets"][0]["relative_path"], "song.mp3")
            self.assertEqual(len(result["assets"][0]["sha256"]), 64)
            self.assertEqual(result["evidence"]["output_ingestion"]["source_mode"], "REFERENCE_ONLY_NO_MOVE")
            self.assertEqual(json.loads(manifest.read_text())["generation"]["status"], "INGESTED")

    def test_rejects_output_outside_governed_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); bench, outputs = root / "bench", root / "outputs"
            bench.mkdir(); outputs.mkdir()
            manifest = bench / "manifest.json"; manifest.write_text(json.dumps(self.manifest()), encoding="utf-8")
            outside = root / "outside.mp3"; outside.write_bytes(b"x")
            with self.assertRaisesRegex(OutputIngestionError, "escapes"):
                OutputIngestor(bench, outputs).ingest(manifest, [outside], {}, provider_id="ace")

    def test_rejects_secret_like_response_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); bench, outputs = root / "bench", root / "outputs"
            bench.mkdir(); outputs.mkdir()
            manifest = bench / "manifest.json"; manifest.write_text(json.dumps(self.manifest()), encoding="utf-8")
            audio = outputs / "song.mp3"; audio.write_bytes(b"x")
            with self.assertRaisesRegex(OutputIngestionError, "secret-like"):
                OutputIngestor(bench, outputs).ingest(manifest, [audio], {"api_key": "must-not-land"}, provider_id="ace")


if __name__ == "__main__":
    unittest.main()
