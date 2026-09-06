import unittest

from projects.ultratrain.method_selector import TrainingMethod
from projects.ultratrain.runtime_policy import RuntimeStatus, route_runtime


class RuntimePolicyTests(unittest.TestCase):
    def test_sft_prefers_trl(self):
        result = route_runtime(TrainingMethod.SFT, {"trl_available": True, "transformers_available": True})
        self.assertEqual(result.status, RuntimeStatus.SUPPORTED)
        self.assertEqual(result.training_engine, "trl")

    def test_dpo_falls_back_to_transformers(self):
        result = route_runtime(TrainingMethod.DPO, {"trl_available": False, "transformers_available": True})
        self.assertEqual(result.training_engine, "transformers")
        self.assertIn("runtime.engine.transformers_fallback", result.decisions)

    def test_grpo_auto_vllm_requires_floor_and_canary(self):
        result = route_runtime(TrainingMethod.GRPO, {
            "trl_available": True, "vllm_available": True,
            "vllm_version": "0.28.0", "vllm_canary_passed": True,
        })
        self.assertEqual(result.rollout_provider, "vllm")

    def test_grpo_stays_inprocess_without_vllm_canary(self):
        result = route_runtime(TrainingMethod.GRPO, {
            "trl_available": True, "vllm_available": True,
            "vllm_version": "0.28.0", "vllm_canary_passed": False,
        })
        self.assertEqual(result.status, RuntimeStatus.SUPPORTED)
        self.assertEqual(result.rollout_provider, "trl_inprocess")

    def test_distillation_requires_teacher(self):
        result = route_runtime(TrainingMethod.DISTILLATION, {"trl_available": True})
        self.assertEqual(result.status, RuntimeStatus.UNSUPPORTED)
        self.assertIn("runtime.distillation.teacher_required", result.rules)

    def test_async_distillation_requests_vllm_teacher_and_canary(self):
        result = route_runtime(TrainingMethod.DISTILLATION, {
            "trl_available": True, "teacher_available": True,
            "async_distillation": True, "vllm_available": True,
            "vllm_version": "0.28.0", "vllm_canary_passed": False,
        })
        self.assertEqual(result.teacher_provider, "vllm")
        self.assertEqual(result.status, RuntimeStatus.NEEDS_CANARY)
        self.assertIn("vllm_runtime", result.canaries)


if __name__ == "__main__":
    unittest.main()
