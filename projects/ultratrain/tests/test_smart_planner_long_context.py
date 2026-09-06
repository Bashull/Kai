import unittest

from projects.ultratrain.long_context_policy import LongContextStatus
from projects.ultratrain.smart_planner import plan_long_context


class SmartPlannerLongContextTests(unittest.TestCase):
    def test_million_token_prefers_cp_when_fsdp2_stack_is_available(self):
        plan = plan_long_context({
            "target_tokens": 1_048_576,
            "native_context_tokens": 40_960,
            "position_extension_strategy": "yarn",
            "fsdp2_available": True,
            "accelerate": "1.14.0",
            "attention": "sdpa",
            "causal_attention": True,
        })
        self.assertEqual(plan.profile["parallelism"], "cp")
        self.assertEqual(plan.profile["backend"], "fsdp2")
        self.assertEqual(plan.profile["loss_type"], "chunked")
        self.assertTrue(plan.profile["expandable_segments"])
        self.assertEqual(plan.status, LongContextStatus.SUPPORTED)

    def test_million_token_falls_back_to_sp_when_cp_is_unavailable(self):
        plan = plan_long_context({
            "target_tokens": 1_048_576,
            "native_context_tokens": 32_768,
            "position_extension_strategy": "yarn",
            "deepspeed_available": True,
            "accelerate": "1.12.0",
            "deepspeed": "0.18.1",
            "parallelism_size": 8,
            "kv_heads": 8,
        })
        self.assertEqual(plan.profile["parallelism"], "sp")
        self.assertEqual(plan.profile["backend"], "deepspeed")
        self.assertEqual(plan.status, LongContextStatus.SUPPORTED)

    def test_sp_is_not_selected_when_parallelism_would_exceed_kv_heads(self):
        plan = plan_long_context({
            "target_tokens": 1_048_576,
            "native_context_tokens": 32_768,
            "position_extension_strategy": "yarn",
            "deepspeed_available": True,
            "accelerate": "1.12.0",
            "deepspeed": "0.18.1",
            "parallelism_size": 16,
            "kv_heads": 8,
        })
        self.assertNotIn("parallelism", plan.profile)
        self.assertEqual(plan.status, LongContextStatus.NEEDS_CANARY)
        self.assertIn("million_token_capacity", plan.canaries)

    def test_explicit_parallelism_is_preserved_and_validated(self):
        plan = plan_long_context({
            "target_tokens": 1_048_576,
            "parallelism": "cp",
            "backend": "deepspeed",
            "accelerate": "1.14.0",
            "expandable_segments": True,
        })
        self.assertEqual(plan.profile["parallelism"], "cp")
        self.assertEqual(plan.status, LongContextStatus.UNSUPPORTED)
        self.assertIn("long_context.cp.requires_fsdp2", plan.rules)

    def test_planner_does_not_invent_position_extension(self):
        plan = plan_long_context({
            "target_tokens": 262_144,
            "native_context_tokens": 32_768,
        })
        self.assertNotIn("position_extension_strategy", plan.profile)
        self.assertEqual(plan.status, LongContextStatus.NEEDS_CANARY)
        self.assertIn("long_context_position_extension", plan.canaries)

    def test_long_context_defaults_to_chunked_loss_without_overriding_explicit_nll(self):
        automatic = plan_long_context({"target_tokens": 262_144, "native_context_tokens": 262_144})
        explicit = plan_long_context({"target_tokens": 262_144, "native_context_tokens": 262_144, "loss_type": "nll"})
        self.assertEqual(automatic.profile["loss_type"], "chunked")
        self.assertEqual(automatic.status, LongContextStatus.SUPPORTED)
        self.assertEqual(explicit.profile["loss_type"], "nll")
        self.assertEqual(explicit.status, LongContextStatus.NEEDS_CANARY)

    def test_planner_does_not_silently_enable_unreleased_activation_offload(self):
        plan = plan_long_context({
            "target_tokens": 262_144,
            "native_context_tokens": 262_144,
            "activation_offload": True,
            "transformers_source": "release",
        })
        self.assertTrue(plan.profile["activation_offload"])
        self.assertEqual(plan.status, LongContextStatus.NEEDS_CANARY)
        self.assertIn("transformers_main_activation_offload", plan.canaries)


if __name__ == "__main__":
    unittest.main()
