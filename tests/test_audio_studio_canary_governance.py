import json
from pathlib import Path
import tempfile
import unittest

from audio_studio.execution import AuthorizationReceipt, ExecutionBlocked
from audio_studio.transports.canary_governance import (
    CanaryEventJournal,
    CanaryPermitLedger,
    classify_error,
    fingerprint_call,
    issue_manual_permit,
    run_governed_canary,
    sanitize_error,
)
from audio_studio.transports.gradio_zerogpu import (
    ZeroGpuCanaryRequest,
    compile_zerogpu_canary,
)


def authorized_call(prompt="test"):
    receipt = AuthorizationReceipt(
        provider_id="ace-step-1.5-zerogpu",
        allowed=True,
        reason="FREE_OR_LOCAL_ROUTE_APPROVED",
        cost_class="FREE",
        estimated_cost_usd=None,
        policy={"free_only": True},
        checked_at="2026-08-27T00:00:00+00:00",
    )
    return compile_zerogpu_canary(ZeroGpuCanaryRequest(prompt), receipt)


class CanaryGovernanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ledger = CanaryPermitLedger(Path(self.temp.name) / "permits.json")
        self.call = authorized_call()
        self.permit = issue_manual_permit(
            self.call,
            permit_id="manual-001",
            approved_by="Asier",
            approved_at="2026-08-27T12:00:00+00:00",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_permit_is_bound_to_exact_call(self):
        self.assertEqual(self.permit.call_fingerprint, fingerprint_call(self.call))
        changed = authorized_call("different")
        with self.assertRaisesRegex(ExecutionBlocked, "PERMIT_CALL_MISMATCH"):
            self.ledger.consume(self.permit, changed)

    def test_permit_is_consumed_before_submit_and_cannot_replay(self):
        seen = []
        result = run_governed_canary(
            self.call,
            self.permit,
            self.ledger,
            lambda call: seen.append(call) or "audio.mp3",
            attempt_id="attempt-001",
            now=lambda: "2026-08-27T12:01:00+00:00",
            monotonic=iter((1.0, 1.5)).__next__,
        )
        self.assertEqual(result.record.status, "SUCCEEDED")
        self.assertEqual(result.record.elapsed_ms, 500)
        self.assertEqual(result.record.output_reference_count, 1)
        self.assertEqual(len(seen), 1)
        with self.assertRaisesRegex(ExecutionBlocked, "PERMIT_ALREADY_CONSUMED"):
            run_governed_canary(
                self.call,
                self.permit,
                self.ledger,
                lambda call: seen.append(call),
                attempt_id="attempt-002",
            )
        self.assertEqual(len(seen), 1)

    def test_upstream_abort_becomes_structured_failure_without_retry(self):
        calls = []
        events = []

        def fail(call):
            calls.append(call)
            raise RuntimeError("GPU task aborted")

        result = run_governed_canary(
            self.call,
            self.permit,
            self.ledger,
            fail,
            attempt_id="attempt-abort",
            event_sink=events.append,
            now=lambda: "2026-08-27T12:01:00+00:00",
            monotonic=iter((1.0, 287.13)).__next__,
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual([event.status for event in events], ["SUBMITTED", "FAILED"])
        self.assertEqual(result.record.error_code, "UPSTREAM_GPU_ABORTED")
        self.assertEqual(result.record.elapsed_ms, 286130)
        self.assertIsNone(result.output)

    def test_ledger_contains_no_prompt_or_token(self):
        self.ledger.consume(self.permit, self.call)
        raw = Path(self.ledger.path).read_text(encoding="utf-8")
        data = json.loads(raw)
        self.assertIn("manual-001", data["consumed_permits"])
        self.assertNotIn("test", raw)
        self.assertNotIn("token", raw.lower())

    def test_error_sanitization_and_classification(self):
        message = sanitize_error(
            "timeout Bearer secret-value hf_123456789 token=topsecret\nnext"
        )
        self.assertNotIn("secret-value", message)
        self.assertNotIn("hf_123456789", message)
        self.assertNotIn("topsecret", message)
        self.assertEqual(classify_error(message), "UPSTREAM_TIMEOUT")
        self.assertEqual(classify_error("queue full"), "QUEUE_FAILURE")
        self.assertEqual(classify_error("quota exceeded"), "QUOTA_EXHAUSTED")

    def test_journal_persists_sanitized_state_transitions(self):
        journal = CanaryEventJournal(Path(self.temp.name) / "attempts.ndjson")

        def fail(call):
            raise RuntimeError("GPU task aborted token=must-not-leak")

        result = run_governed_canary(
            self.call,
            self.permit,
            self.ledger,
            fail,
            attempt_id="attempt-journal",
            event_sink=journal.append,
            now=lambda: "2026-08-27T12:01:00+00:00",
            monotonic=iter((1.0, 2.0)).__next__,
        )
        records = journal.read_all()
        self.assertEqual([record.status for record in records], ["SUBMITTED", "FAILED"])
        self.assertEqual(records[-1], result.record)
        raw = Path(journal.path).read_text(encoding="utf-8")
        self.assertNotIn("must-not-leak", raw)


if __name__ == "__main__":
    unittest.main()
