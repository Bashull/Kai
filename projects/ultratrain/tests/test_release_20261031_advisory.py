"""Focused synthetic candidate tests. No GPU, kernel or runtime proof."""
import unittest
from projects.ultratrain.release_20261031_advisory import assess_20261031 as assess


def rules(profile):
    return {x["rule"]: x["status"] for x in assess(profile)["findings"]}


class UltraTrain1031Advisory(unittest.TestCase):
    def test_never_promotes(self):
        self.assertFalse(assess({})["allow_continue"])
    def test_invalid_profile(self):
        self.assertIn("release1031.profile_shape", rules({"packages": []}))
    def test_fp8_eager_requires_gradients(self):
        p = {"packages": {"transformers": "5.22.0"},
             "training": {"adapter_training": True},
             "quantization": {"base_weight_format": "fp8", "expert_matmul_backend": "eager"}}
        self.assertIn("tf522.fp8_gradient_parity", rules(p))
    def test_fp8_deepgemm_not_supported(self):
        p = {"packages": {"transformers": "5.22.1"},
             "training": {"adapter_training": True},
             "quantization": {"base_weight_format": "fp8", "expert_matmul_backend": "deepgemm"}}
        self.assertEqual(rules(p)["tf522.fp8_backward_unimplemented_backend"], "UNSUPPORTED")
    def test_fp4_backward_not_supported(self):
        p = {"packages": {"transformers": "5.22.0"},
             "training": {"adapter_training": True},
             "quantization": {"base_weight_format": "fp4", "needs_input_backward": True}}
        self.assertIn("tf522.fp4_backward_not_supported", rules(p))
    def test_ep_import_migration(self):
        p = {"packages": {"transformers": "5.22.0"},
             "distributed": {"custom_ep_extensions": True, "old_ep_import": True, "old_ep_base_class": True}}
        self.assertIn("tf522.ep_extension_migration", rules(p))
        self.assertIn("tf522.ep_import_deprecation", rules(p))
    def test_remote_code_pin(self):
        p = {"packages": {"transformers": "5.22.0"}, "pipeline": {"uses_remote_code": True}}
        self.assertIn("tf522.remote_code_unpinned", rules(p))
    def test_mistral_license(self):
        p = {"packages": {"transformers": "5.22.0"},
             "model": {"family": "mistral_large_4", "business_model": "model_as_a_service"}}
        self.assertEqual(rules(p)["tf522.mistral4_maas_license"], "UNSUPPORTED")
    def test_torchtitan_torch_214_not_hard_blocked(self):
        p = {"packages": {"torchtitan": "0.4.0", "torch": "2.14.1"}, "torchtitan": {"enabled": True}}
        self.assertEqual(rules(p)["titan040.torch_alignment"], "NEEDS_CANARY")
    def test_torchtitan_mxfp8_nightly(self):
        p = {"packages": {"torchtitan": "0.4.0", "torch": "2.15.0"},
             "torchtitan": {"enabled": True}, "training": {"mxfp8": True}}
        self.assertEqual(rules(p)["titan040.mxfp8_torchao_nightly"], "UNSUPPORTED")
    def test_torchtitan_grain_dcp(self):
        p = {"packages": {"torchtitan": "0.4.0", "torch": "2.15.0"},
             "torchtitan": {"enabled": True}, "data": {"grain_pipeline": True},
             "checkpoint": {"hf_dcp": True}}
        self.assertIn("titan040.grain_resume", rules(p))
        self.assertIn("titan040.dcp_resume", rules(p))
    def test_sdc_determinism(self):
        p = {"packages": {"torchtitan": "0.4.0", "torch": "2.15.0"},
             "torchtitan": {"enabled": True}, "training": {"sdc_replay": True}}
        self.assertIn("titan040.sdc_requires_determinism", rules(p))
    def test_titanrl_session_kv(self):
        p = {"packages": {"torchtitan": "0.4.0", "torch": "2.15.0"},
             "torchtitan": {"enabled": True},
             "rl": {"titanrl": True, "multiturn_kv_reuse": True, "import_path": "torchtitan.experiments.rl"}}
        self.assertIn("titan040.session_kv_isolation", rules(p))
        self.assertIn("titan040.titanrl_import_moved", rules(p))
    def test_deterministic_order(self):
        p = {"packages": {"transformers": "5.22.0", "torchtitan": "0.4.0", "torch": "2.14.1"},
             "torchtitan": {"enabled": True}, "training": {"adapter_training": True},
             "quantization": {"base_weight_format": "fp8", "expert_matmul_backend": "deepgemm"}}
        self.assertEqual(assess(p), assess(p))
        self.assertEqual(assess(p)["status"], "UNSUPPORTED")


if __name__ == "__main__":
    unittest.main()
