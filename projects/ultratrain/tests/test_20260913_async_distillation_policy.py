import unittest

from projects.ultratrain.async_distillation_policy import (
    AsyncDistillationStatus,
    AsyncTeacherServer,
    plan_async_distillation,
)


class AsyncDistillationPolicyTests(unittest.TestCase):
    def teacher(self, teacher_id="default", **overrides):
        values = {
            "teacher_id": teacher_id,
            "url": "http://127.0.0.1:8001",
            "tokenizer_id": "tok",
            "processed_logprobs": True,
            "max_logprobs_unlimited": True,
            "identity_canary_passed": True,
        }
        values.update(overrides)
        return AsyncTeacherServer(**values)

    def plan(self, **overrides):
        values = {
            "trl_version": "1.13.0",
            "vllm_version": "0.29.0",
            "student_server_url": "http://127.0.0.1:8000",
            "student_tokenizer_id": "tok",
            "teachers": (self.teacher(),),
            "student_server_dev_mode": True,
            "student_weight_transfer_backend": "nccl",
            "vllm_runtime_canary_passed": True,
        }
        values.update(overrides)
        return plan_async_distillation(**values)

    def test_green_path_reuses_upstream_async_trainer_with_full_nccl(self):
        plan = self.plan()
        self.assertEqual(plan.status, AsyncDistillationStatus.SUPPORTED)
        self.assertEqual(plan.weight_delta_transport, "full_nccl")
        self.assertEqual(plan.config_kwargs["teacher_server_urls"], {"default": "http://127.0.0.1:8001"})

    def test_ultratrain_keeps_vllm_security_floor_028(self):
        self.assertEqual(self.plan(vllm_version="0.27.1").status, AsyncDistillationStatus.UNSUPPORTED)

    def test_unknown_vllm_identity_requires_canary(self):
        self.assertEqual(self.plan(vllm_version=None).status, AsyncDistillationStatus.NEEDS_CANARY)

    def test_teacher_tokenizer_mismatch_is_unsupported(self):
        self.assertEqual(
            self.plan(teachers=(self.teacher(tokenizer_id="other"),)).status,
            AsyncDistillationStatus.UNSUPPORTED,
        )

    def test_teacher_requires_processed_logprobs(self):
        self.assertEqual(
            self.plan(teachers=(self.teacher(processed_logprobs=False),)).status,
            AsyncDistillationStatus.UNSUPPORTED,
        )

    def test_topk_above_vllm_default_cap_requires_unlimited_logprobs(self):
        self.assertEqual(
            self.plan(teacher_top_k=64, teachers=(self.teacher(max_logprobs_unlimited=False),)).status,
            AsyncDistillationStatus.UNSUPPORTED,
        )

    def test_missing_runtime_evidence_stays_canary_gated(self):
        plan = self.plan(student_server_dev_mode=None, vllm_runtime_canary_passed=None)
        self.assertEqual(plan.status, AsyncDistillationStatus.NEEDS_CANARY)
        self.assertIn("async_student_dev_mode", plan.canaries)
        self.assertIn("async_vllm_runtime", plan.canaries)

    def test_advanced_weight_delta_is_not_claimed_by_upstream_adapter(self):
        self.assertEqual(
            self.plan(requested_weight_delta="sharded_rdt").status,
            AsyncDistillationStatus.UNSUPPORTED,
        )

    def test_context_or_sequence_parallelism_is_blocked(self):
        self.assertEqual(self.plan(sequence_parallelism="cp").status, AsyncDistillationStatus.UNSUPPORTED)

    def test_non_loopback_plain_http_teacher_is_rejected(self):
        with self.assertRaises(ValueError):
            self.teacher(url="http://example.test:8001")

    def test_multi_teacher_urls_are_preserved_for_mopd(self):
        plan = self.plan(
            teachers=(
                self.teacher("math"),
                self.teacher("code", url="http://127.0.0.1:8002"),
            )
        )
        self.assertEqual(plan.config_kwargs["teacher_server_urls"]["code"], "http://127.0.0.1:8002")

    def test_adapter_is_pinned_to_exact_trl_113(self):
        self.assertEqual(self.plan(trl_version="1.13.1").status, AsyncDistillationStatus.UNSUPPORTED)


if __name__ == "__main__":
    unittest.main()
