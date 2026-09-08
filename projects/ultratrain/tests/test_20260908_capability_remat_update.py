import unittest

from projects.ultratrain.activation_checkpoint_policy import (
    ActivationCheckpointStatus,
    plan_activation_checkpointing,
)
from projects.ultratrain.long_context_policy import LongContextStatus, evaluate_long_context_profile


class September8CapabilityUpdateTests(unittest.TestCase):
    def test_context_parallel_rejects_model_declared_unsupported(self):
        result = evaluate_long_context_profile({
            "target_tokens": 1_048_576,
            "parallelism": "cp",
            "backend": "fsdp2",
            "accelerate": "1.14.0",
            "model_supports_context_parallel": False,
            "expandable_segments": True,
        })
        self.assertEqual(result.status, LongContextStatus.UNSUPPORTED)
        self.assertIn("long_context.cp.model_unsupported", result.rules)

    def test_context_parallel_preserves_legacy_when_capability_is_unknown(self):
        result = evaluate_long_context_profile({
            "target_tokens": 1_048_576,
            "parallelism": "cp",
            "backend": "fsdp2",
            "accelerate": "1.14.0",
            "expandable_segments": True,
        })
        self.assertEqual(result.status, LongContextStatus.SUPPORTED)

    def test_region_remat_requires_canary(self):
        plan = plan_activation_checkpointing({
            "activation_checkpointing": "region_remat",
            "torchtitan_available": True,
            "torch_remat_available": True,
            "activation_save_regions": ["attention.qkv", "attention.wo"],
        })
        self.assertEqual(plan.status, ActivationCheckpointStatus.NEEDS_CANARY)
        self.assertEqual(plan.save_regions, ("attention.qkv", "attention.wo"))
        self.assertIn("torchtitan_region_remat", plan.canaries)

    def test_region_remat_rejects_implicit_rng_preservation(self):
        plan = plan_activation_checkpointing({
            "activation_checkpointing": "region_remat",
            "torchtitan_available": True,
            "torch_remat_available": True,
            "preserve_rng_state": True,
        })
        self.assertEqual(plan.status, ActivationCheckpointStatus.UNSUPPORTED)
        self.assertIn("activation_checkpoint.region_remat.requires_explicit_rng_hooks", plan.rules)

    def test_region_remat_can_promote_after_canary(self):
        plan = plan_activation_checkpointing({
            "activation_checkpointing": "region_remat",
            "torchtitan_available": True,
            "torch_remat_available": True,
            "region_remat_canary_passed": True,
            "activation_save_regions": ["attention.*"],
        })
        self.assertEqual(plan.status, ActivationCheckpointStatus.SUPPORTED)
        self.assertEqual(plan.save_regions, ("attention.*",))


if __name__ == "__main__":
    unittest.main()
