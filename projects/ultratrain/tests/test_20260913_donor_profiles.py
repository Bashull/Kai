import unittest

from projects.ultratrain.donor_profiles import (
    qwen38_27b_uncensored_mlx_profile,
    qwen38_mlx_memory_estimate,
    unsloth_2026_9_4_studio_runtime_descriptor,
)
from projects.ultratrain.hardware_doctor_contract import CapabilityState


class DonorProfilesTests(unittest.TestCase):
    def test_unsloth_studio_profile_is_isolated_and_exact(self):
        runtime = unsloth_2026_9_4_studio_runtime_descriptor()
        versions = {item.name: item.version for item in runtime.packages}
        self.assertEqual(versions["unsloth"], "2026.9.4")
        self.assertEqual(versions["trl"], "0.23.1")
        self.assertEqual(versions["transformers"], "5.5.0")
        self.assertEqual(runtime.isolation, "process")
        self.assertTrue(runtime.requires_isolation)
        self.assertIn("canonical:trl>=1.13.0", runtime.conflicts)

    def test_donor_code_presence_is_declared_not_probed(self):
        runtime = unsloth_2026_9_4_studio_runtime_descriptor()
        self.assertEqual(runtime.capability_state("model.qwen3_8"), CapabilityState.DECLARED)
        self.assertEqual(runtime.capability_state("export.gguf"), CapabilityState.DECLARED)
        self.assertNotEqual(runtime.capability_state("export.gguf"), CapabilityState.PROBED)

    def test_qwen_profile_carries_architecture_and_safety_boundary(self):
        profile = qwen38_27b_uncensored_mlx_profile()
        resolved = profile.resolved_capabilities()
        self.assertEqual(profile.family, "qwen3_5")
        self.assertEqual(resolved["architecture"], "Qwen3_5ForConditionalGeneration")
        self.assertEqual(resolved["max_context"], 262144)
        self.assertEqual(resolved["kv_heads"], 4)
        self.assertTrue(resolved["tool_calls"])
        self.assertTrue(resolved["thinking"])
        self.assertTrue(resolved["refusal_behavior_modified"])
        self.assertNotIn("safe_autonomous_tools", resolved)

    def test_qwen_mlx_memory_estimates_use_observed_lfs_payload_sizes(self):
        four = qwen38_mlx_memory_estimate(4)
        self.assertEqual(four.bytes_required, 16_074_530_924)
        self.assertEqual(four.basis, "estimated")
        self.assertIn("weights-only-lfs-payload", four.assumptions)
        self.assertIn("kv-cache-not-included", four.assumptions)

    def test_two_bit_profile_marks_degradation_risk(self):
        two = qwen38_mlx_memory_estimate(2)
        self.assertEqual(two.bytes_required, 9_351_192_422)
        self.assertIn("donor-card-severely-degraded", two.assumptions)
        self.assertLess(two.confidence, qwen38_mlx_memory_estimate(4).confidence)

    def test_unknown_quantization_is_rejected(self):
        with self.assertRaises(ValueError):
            qwen38_mlx_memory_estimate(3)


if __name__ == "__main__":
    unittest.main()
