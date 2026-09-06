import unittest

from projects.ultratrain.compatibility_core import Decision
from projects.ultratrain.method_selector import TrainingMethod
from projects.ultratrain.smart_planner import plan_training


class TrainingSmartPlannerTests(unittest.TestCase):
    def test_sft_baseline_composes_supported_plan(self):
        plan = plan_training({"profile_id": "sft", "trl_available": True})
        self.assertEqual(plan.method, TrainingMethod.SFT)
        self.assertEqual(plan.runtime.training_engine, "trl")
        self.assertEqual(plan.kernel.backend, "sdpa")
        self.assertEqual(plan.status, Decision.SUPPORTED)

    def test_preference_pairs_auto_select_dpo(self):
        plan = plan_training({"profile_id": "dpo", "preference_pairs": True, "trl_available": True})
        self.assertEqual(plan.method, TrainingMethod.DPO)
        self.assertEqual(plan.status, Decision.SUPPORTED)

    def test_ambiguous_method_blocks_before_runtime_guessing(self):
        plan = plan_training({
            "profile_id": "ambiguous", "trl_available": True,
            "preference_pairs": True, "reward_signal": True,
        })
        self.assertIsNone(plan.method)
        self.assertIsNone(plan.runtime)
        self.assertEqual(plan.status, Decision.NEEDS_CANARY)
        self.assertIn("method_signal_ambiguity", plan.canaries)

    def test_grpo_secure_vllm_route_can_be_supported(self):
        plan = plan_training({
            "profile_id": "grpo", "reward_signal": True,
            "trl_available": True, "trl_version": "1.11.0",
            "vllm_available": True, "vllm_version": "0.28.0",
            "vllm_canary_passed": True, "trl_vllm_canary_passed": True,
        })
        self.assertEqual(plan.method, TrainingMethod.GRPO)
        self.assertEqual(plan.runtime.rollout_provider, "vllm")
        self.assertEqual(plan.status, Decision.SUPPORTED)

    def test_explicit_unverified_liger_keeps_plan_in_canary(self):
        plan = plan_training({
            "profile_id": "liger", "trl_available": True,
            "kernel_preference": "liger", "liger_available": True,
            "liger_canary_passed": False,
        })
        self.assertEqual(plan.kernel.backend, "liger")
        self.assertEqual(plan.status, Decision.NEEDS_CANARY)
        self.assertIn("liger_correctness", plan.canaries)

    def test_async_distillation_is_rejected_by_existing_transformers_gate(self):
        plan = plan_training({
            "profile_id": "distill", "method": "distillation",
            "trl_available": True, "teacher_available": True,
            "async_distillation": True,
            "vllm_available": True, "vllm_version": "0.28.0",
            "vllm_canary_passed": True,
            "packages": {"transformers": "5.1.0"},
        })
        self.assertEqual(plan.status, Decision.UNSUPPORTED)
        self.assertIn("trl.async_distillation.requires_transformers_52", plan.rules)

    def test_million_token_dpo_composes_cp_long_context(self):
        plan = plan_training({
            "profile_id": "long-dpo", "preference_pairs": True,
            "trl_available": True,
            "target_tokens": 1_048_576,
            "native_context_tokens": 40_960,
            "position_extension_strategy": "yarn",
            "fsdp2_available": True,
            "accelerate": "1.14.0",
            "attention": "sdpa", "causal_attention": True,
        })
        self.assertEqual(plan.method, TrainingMethod.DPO)
        self.assertIsNotNone(plan.long_context)
        self.assertEqual(plan.long_context.profile["parallelism"], "cp")
        self.assertEqual(plan.status, Decision.SUPPORTED)
        self.assertIn("long_context.parallelism.cp_selected", plan.decisions)


if __name__ == "__main__":
    unittest.main()
