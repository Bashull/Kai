import unittest

from projects.ultratrain.peft_policy import PeftStatus, evaluate_peft_profile


class PeftTrainableTokensGuardTests(unittest.TestCase):
    def test_bias_output_head_requires_pretraining_logit_canary(self):
        result = evaluate_peft_profile({
            "peft": {
                "trainable_tokens": True,
                "output_head_has_bias": True,
            }
        })
        self.assertEqual(result.status, PeftStatus.NEEDS_CANARY)
        self.assertIn("peft_adapter_init_logits_equal", result.canaries)

    def test_lora_trainable_token_indices_has_same_guard(self):
        result = evaluate_peft_profile({
            "peft": {
                "lora_trainable_token_indices": True,
                "output_head_has_bias": True,
            }
        })
        self.assertEqual(result.status, PeftStatus.NEEDS_CANARY)

    def test_verified_logit_equivalence_promotes_path(self):
        result = evaluate_peft_profile({
            "peft": {
                "trainable_tokens": True,
                "output_head_has_bias": True,
                "adapter_init_logits_equal_canary_passed": True,
            }
        })
        self.assertEqual(result.status, PeftStatus.SUPPORTED)

    def test_explicit_fixed_build_promotes_path(self):
        result = evaluate_peft_profile({
            "peft": {
                "trainable_tokens": True,
                "output_head_has_bias": True,
                "trainable_tokens_bias_fix_present": True,
            }
        })
        self.assertEqual(result.status, PeftStatus.SUPPORTED)

    def test_unknown_output_head_bias_requires_identity_probe(self):
        result = evaluate_peft_profile({"peft": {"trainable_tokens": True}})
        self.assertEqual(result.status, PeftStatus.NEEDS_CANARY)
        self.assertIn("peft_output_head_bias_identity", result.canaries)

    def test_biasless_head_is_not_affected(self):
        result = evaluate_peft_profile({
            "peft": {
                "trainable_tokens": True,
                "output_head_has_bias": False,
            }
        })
        self.assertEqual(result.status, PeftStatus.SUPPORTED)


if __name__ == "__main__":
    unittest.main()
