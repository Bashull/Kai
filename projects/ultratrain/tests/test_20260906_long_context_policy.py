import unittest

from projects.ultratrain.long_context_policy import LongContextStatus, evaluate_long_context_profile


class LongContextPolicyTests(unittest.TestCase):
    def test_cp_requires_fsdp2(self):
        result = evaluate_long_context_profile({"target_tokens": 1_048_576, "parallelism": "cp", "backend": "deepspeed", "accelerate": "1.12.0"})
        self.assertEqual(result.status, LongContextStatus.UNSUPPORTED)
        self.assertIn("long_context.cp.requires_fsdp2", result.rules)

    def test_cp_requires_accelerate_111(self):
        result = evaluate_long_context_profile({"target_tokens": 1_048_576, "parallelism": "cp", "backend": "fsdp2", "accelerate": "1.10.0"})
        self.assertEqual(result.status, LongContextStatus.UNSUPPORTED)

    def test_sp_requires_deepspeed_stack(self):
        result = evaluate_long_context_profile({"target_tokens": 1_048_576, "parallelism": "sp", "backend": "deepspeed", "accelerate": "1.12.0", "deepspeed": "0.18.0"})
        self.assertEqual(result.status, LongContextStatus.UNSUPPORTED)
        self.assertIn("long_context.sp.requires_deepspeed_0181", result.rules)

    def test_sp_cannot_exceed_kv_heads(self):
        result = evaluate_long_context_profile({"target_tokens": 1_048_576, "parallelism": "sp", "parallelism_size": 16, "kv_heads": 8, "backend": "deepspeed", "accelerate": "1.12.0", "deepspeed": "0.18.1"})
        self.assertEqual(result.status, LongContextStatus.UNSUPPORTED)

    def test_activation_offload_is_not_release_capability_yet(self):
        result = evaluate_long_context_profile({"target_tokens": 262_144, "activation_offload": True, "transformers_source": "release"})
        self.assertEqual(result.status, LongContextStatus.NEEDS_CANARY)
        self.assertIn("transformers_main_activation_offload", result.canaries)

    def test_extension_beyond_native_context_requires_position_strategy(self):
        result = evaluate_long_context_profile({"target_tokens": 160_000, "native_context_tokens": 40_960})
        self.assertEqual(result.status, LongContextStatus.NEEDS_CANARY)
        self.assertIn("long_context_position_extension", result.canaries)

    def test_million_token_profile_requires_allocator_guard(self):
        result = evaluate_long_context_profile({"target_tokens": 1_048_576, "native_context_tokens": 40_960, "position_extension_strategy": "yarn", "parallelism": "cp", "backend": "fsdp2", "accelerate": "1.14.0", "activation_offload": True, "transformers_source": "main", "expandable_segments": False})
        self.assertEqual(result.status, LongContextStatus.NEEDS_CANARY)
        self.assertIn("cuda_allocator_fragmentation", result.canaries)


if __name__ == "__main__":
    unittest.main()
