import unittest

from projects.ultratrain.compatibility_core import Decision, evaluate_profile


class TRL111CompatibilityTests(unittest.TestCase):
    def test_trl_server_mode_with_vllm_028_requires_cross_version_canary(self):
        r = evaluate_profile({
            "profile_id": "trl-server",
            "trl": {"version": "1.11.0", "vllm_server_mode": True},
            "runtime": {"vllm": True, "vllm_version": "0.28.0", "vllm_canary_passed": True},
        })
        self.assertEqual(r.status, Decision.NEEDS_CANARY)
        self.assertIn("trl_vllm_server_compatibility", r.canaries)

    def test_trl_server_mode_can_continue_after_cross_version_canary(self):
        r = evaluate_profile({
            "profile_id": "trl-server-ok",
            "trl": {"version": "1.11.0", "vllm_server_mode": True, "vllm_028_canary_passed": True},
            "runtime": {"vllm": True, "vllm_version": "0.28.0", "vllm_canary_passed": True},
        })
        self.assertEqual(r.status, Decision.SUPPORTED)

    def test_packing_with_context_parallelism_is_unsupported(self):
        r = evaluate_profile({
            "profile_id": "trl-pack-cp",
            "trl": {"version": "1.11.0", "packing": True},
            "distributed": {"context_parallelism": True},
        })
        self.assertEqual(r.status, Decision.UNSUPPORTED)

    def test_async_distillation_requires_vllm(self):
        r = evaluate_profile({
            "profile_id": "async-distill-no-vllm",
            "trl": {"version": "1.11.0", "async_distillation": True},
            "packages": {"transformers": "5.2.0"},
        })
        self.assertEqual(r.status, Decision.UNSUPPORTED)

    def test_async_distillation_requires_transformers_52(self):
        r = evaluate_profile({
            "profile_id": "async-distill-old-transformers",
            "trl": {"version": "1.11.0", "async_distillation": True},
            "runtime": {"vllm": True, "vllm_version": "0.28.0", "vllm_canary_passed": True},
            "packages": {"transformers": "5.1.0"},
        })
        self.assertEqual(r.status, Decision.UNSUPPORTED)

    def test_async_distillation_distributed_requires_fsdp2(self):
        r = evaluate_profile({
            "profile_id": "async-distill-ddp",
            "trl": {"version": "1.11.0", "async_distillation": True},
            "runtime": {"vllm": True, "vllm_version": "0.28.0", "vllm_canary_passed": True},
            "packages": {"transformers": "5.2.0"},
            "distributed": {"enabled": True, "fsdp_version": 1},
        })
        self.assertEqual(r.status, Decision.UNSUPPORTED)

    def test_trl_112_is_not_treated_as_new_feature_epoch(self):
        r = evaluate_profile({
            "profile_id": "trl-duplicate",
            "trl": {"version": "1.12.0", "vllm_server_mode": True},
            "runtime": {"vllm": True, "vllm_version": "0.28.0", "vllm_canary_passed": True},
        })
        self.assertEqual(r.status, Decision.NEEDS_CANARY)


if __name__ == "__main__":
    unittest.main()
