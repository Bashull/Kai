import unittest

from projects.ultratrain.compatibility_core import Decision, evaluate_profile
from projects.ultratrain.long_context_policy import LongContextStatus, evaluate_long_context_profile
from projects.ultratrain.smart_planner import plan_long_context


class TRL113PolicyTests(unittest.TestCase):
    def test_activation_offload_is_supported_with_transformers_516_release(self):
        result = evaluate_long_context_profile({
            "target_tokens": 262_144,
            "native_context_tokens": 262_144,
            "activation_offload": True,
            "transformers_source": "release",
            "transformers_version": "5.16.0",
        })
        self.assertEqual(result.status, LongContextStatus.SUPPORTED)

    def test_activation_offload_rejects_transformers_below_516(self):
        result = evaluate_long_context_profile({
            "target_tokens": 262_144,
            "native_context_tokens": 262_144,
            "activation_offload": True,
            "transformers_source": "release",
            "transformers_version": "5.15.1",
        })
        self.assertEqual(result.status, LongContextStatus.UNSUPPORTED)
        self.assertIn("long_context.activation_offload.requires_transformers_516", result.rules)

    def test_trl_113_sequence_parallel_requires_deepspeed_0186(self):
        result = evaluate_long_context_profile({
            "target_tokens": 1_048_576,
            "native_context_tokens": 1_048_576,
            "parallelism": "sp",
            "backend": "deepspeed",
            "accelerate": "1.14.0",
            "deepspeed": "0.18.1",
            "trl_version": "1.13.0",
            "parallelism_size": 8,
            "kv_heads": 8,
            "expandable_segments": True,
        })
        self.assertEqual(result.status, LongContextStatus.UNSUPPORTED)
        self.assertIn("long_context.sp.trl_113_requires_deepspeed_0186", result.rules)

    def test_trl_113_peft_usage_requires_peft_013(self):
        result = evaluate_profile({
            "profile_id": "trl113-peft-floor",
            "trl": {"version": "1.13.0"},
            "peft": {"lora": True},
            "packages": {"peft": "0.12.0"},
        })
        self.assertEqual(result.status, Decision.UNSUPPORTED)
        self.assertIn("trl.113.requires_peft_013", result.rules)

    def test_trl_113_deepspeed_backend_requires_0186(self):
        result = evaluate_profile({
            "profile_id": "trl113-deepspeed-floor",
            "trl": {"version": "1.13.0"},
            "distributed": {"enabled": True, "backend": "deepspeed"},
            "packages": {"deepspeed": "0.18.1"},
        })
        self.assertEqual(result.status, Decision.UNSUPPORTED)
        self.assertIn("trl.113.requires_deepspeed_0186", result.rules)

    def test_trl_113_chunked_loss_surfaces_tensorcore_fastpath(self):
        plan = plan_long_context({
            "target_tokens": 262_144,
            "native_context_tokens": 262_144,
            "trl_version": "1.13.0",
        })
        self.assertEqual(plan.profile["loss_type"], "chunked")
        self.assertIn("long_context.loss.trl_113_tensorcore_fastpath", plan.decisions)


if __name__ == "__main__":
    unittest.main()
