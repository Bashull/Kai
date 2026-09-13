import json
import unittest

from projects.ultratrain.teacher_provider import (
    TeacherCanaryEvidence,
    TeacherEndpoint,
    TeacherIdentity,
    TeacherProviderStatus,
    evaluate_remote_teacher,
)


class TeacherProviderTests(unittest.TestCase):
    def identity(self):
        return TeacherIdentity("teacher/model", "abc123", "shared/tokenizer", 32000)

    def endpoint(self, **kwargs):
        values = {
            "provider_id": "teacher-vllm",
            "base_url": "https://teacher.example.test",
            "auth_mode": "bearer_ref",
            "credential_ref": "vault://teacher-token",
        }
        values.update(kwargs)
        return TeacherEndpoint(**values)

    def green_evidence(self):
        return TeacherCanaryEvidence(True, True, True, True, True, True, ("canary://run-1",))

    def test_public_http_endpoint_is_rejected(self):
        with self.assertRaises(ValueError):
            self.endpoint(base_url="http://teacher.example.test")

    def test_loopback_http_endpoint_is_allowed(self):
        endpoint = self.endpoint(base_url="http://127.0.0.1:9000")
        self.assertEqual(endpoint.base_url, "http://127.0.0.1:9000")

    def test_bearer_auth_stores_only_credential_reference(self):
        payload = self.endpoint().to_safe_dict()
        self.assertEqual(payload["credential_ref"], "vault://teacher-token")
        self.assertNotIn("token", payload)
        self.assertNotIn("authorization", payload)

    def test_missing_canaries_block_promotion(self):
        plan = evaluate_remote_teacher(
            self.endpoint(), self.identity(), TeacherCanaryEvidence(),
            student_tokenizer_id="shared/tokenizer", student_vocab_size=32000,
        )
        self.assertEqual(plan.status, TeacherProviderStatus.NEEDS_CANARY)
        self.assertIn("teacher_full_vocab_logits", plan.canaries)
        self.assertFalse(plan.allow_continue)

    def test_full_green_canary_promotes_remote_teacher(self):
        plan = evaluate_remote_teacher(
            self.endpoint(), self.identity(), self.green_evidence(),
            student_tokenizer_id="shared/tokenizer", student_vocab_size=32000,
        )
        self.assertEqual(plan.status, TeacherProviderStatus.SUPPORTED)
        self.assertTrue(plan.allow_continue)

    def test_vocab_mismatch_is_hard_failure(self):
        plan = evaluate_remote_teacher(
            self.endpoint(), self.identity(), self.green_evidence(),
            student_tokenizer_id="shared/tokenizer", student_vocab_size=64000,
        )
        self.assertEqual(plan.status, TeacherProviderStatus.UNSUPPORTED)
        self.assertIn("teacher.vocab.incompatible", plan.rules)

    def test_tokenizer_mismatch_is_hard_failure(self):
        plan = evaluate_remote_teacher(
            self.endpoint(), self.identity(), self.green_evidence(),
            student_tokenizer_id="other/tokenizer", student_vocab_size=32000,
        )
        self.assertEqual(plan.status, TeacherProviderStatus.UNSUPPORTED)

    def test_text_only_or_partial_logprobs_are_not_enough(self):
        ev = TeacherCanaryEvidence(True, True, True, True, False, True)
        plan = evaluate_remote_teacher(
            self.endpoint(), self.identity(), ev,
            student_tokenizer_id="shared/tokenizer", student_vocab_size=32000,
        )
        self.assertEqual(plan.status, TeacherProviderStatus.UNSUPPORTED)
        self.assertIn("teacher.full_vocab_logits.required", plan.rules)

    def test_failed_remote_teacher_can_fallback_to_local(self):
        ev = TeacherCanaryEvidence(False, True, True, True, True, True)
        plan = evaluate_remote_teacher(
            self.endpoint(), self.identity(), ev,
            student_tokenizer_id="shared/tokenizer", student_vocab_size=32000,
            fallback_teacher_model="local/teacher",
        )
        self.assertEqual(plan.status, TeacherProviderStatus.FALLBACK)
        self.assertTrue(plan.allow_continue)
        self.assertEqual(plan.fallback_teacher_model, "local/teacher")

    def test_json_is_deterministic_and_contains_no_secret_value(self):
        plan = evaluate_remote_teacher(
            self.endpoint(), self.identity(), self.green_evidence(),
            student_tokenizer_id="shared/tokenizer", student_vocab_size=32000,
        )
        first = plan.to_json()
        self.assertEqual(first, plan.to_json())
        payload = json.loads(first)
        self.assertEqual(payload["endpoint"]["credential_ref"], "vault://teacher-token")
        self.assertNotIn("secret", first.lower())


if __name__ == "__main__":
    unittest.main()
