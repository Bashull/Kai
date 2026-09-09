import unittest

from projects.ultratrain.kernel_policy import route_kernel


class LigerPreferenceFastpathTests(unittest.TestCase):
    def test_verified_dpo_peft_frozen_head_surfaces_fastpath(self):
        result = route_kernel({
            "method": "dpo",
            "peft": {"lora": True},
            "preference_head_frozen": True,
            "prefer_fused_kernels": True,
            "liger_available": True,
            "liger_canary_passed": True,
            "liger_preference_frozen_weight_fastpath": True,
        })
        self.assertEqual(result.backend, "liger")
        self.assertIn("kernel.liger.preference_frozen_weight_fastpath", result.decisions)

    def test_unambiguous_preference_signal_is_enough_for_dpo_fastpath(self):
        result = route_kernel({
            "preference_pairs": True,
            "peft_enabled": True,
            "preference_head_frozen": True,
            "prefer_fused_kernels": True,
            "liger_available": True,
            "liger_canary_passed": True,
            "liger_preference_frozen_weight_fastpath": True,
        })
        self.assertIn("kernel.liger.preference_frozen_weight_fastpath", result.decisions)

    def test_ambiguous_method_signals_do_not_claim_dpo_fastpath(self):
        result = route_kernel({
            "preference_pairs": True,
            "reward_signal": True,
            "peft_enabled": True,
            "preference_head_frozen": True,
            "prefer_fused_kernels": True,
            "liger_available": True,
            "liger_canary_passed": True,
            "liger_preference_frozen_weight_fastpath": True,
        })
        self.assertNotIn("kernel.liger.preference_frozen_weight_fastpath", result.decisions)

    def test_does_not_claim_fastpath_without_capability_evidence(self):
        result = route_kernel({
            "method": "dpo",
            "peft_enabled": True,
            "preference_head_frozen": True,
            "prefer_fused_kernels": True,
            "liger_available": True,
            "liger_canary_passed": True,
        })
        self.assertNotIn("kernel.liger.preference_frozen_weight_fastpath", result.decisions)


if __name__ == "__main__":
    unittest.main()
