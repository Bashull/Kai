import unittest

from projects.ultratrain.compatibility_core import Decision, evaluate_profile


class UpdateWatch20260828Tests(unittest.TestCase):
    def test_vllm_below_security_floor_is_unsupported(self):
        r = evaluate_profile({
            "profile_id": "p",
            "runtime": {"vllm": True, "vllm_version": "0.26.0", "vllm_canary_passed": True},
        })
        self.assertEqual(r.status, Decision.UNSUPPORTED)
        self.assertIn("runtime.vllm.security_floor", r.rules)

    def test_vllm_security_floor_still_requires_runtime_canary(self):
        r = evaluate_profile({
            "profile_id": "p",
            "runtime": {"vllm": True, "vllm_version": "0.27.0"},
        })
        self.assertEqual(r.status, Decision.NEEDS_CANARY)
        self.assertIn("vllm_runtime", r.canaries)
    def test_megatron_multigrid_requires_explicit_process_groups(self):
        r = evaluate_profile({
            "profile_id": "p",
            "megatron": {
                "enabled": True,
                "multi_grid": True,
                "explicit_process_groups": False,
            },
        })
        self.assertEqual(r.status, Decision.UNSUPPORTED)
        self.assertIn("megatron.multigrid.explicit_process_groups", r.rules)

    def test_megatron_multigrid_with_explicit_groups_is_supported(self):
        r = evaluate_profile({
            "profile_id": "p",
            "megatron": {
                "enabled": True,
                "multi_grid": True,
                "explicit_process_groups": True,
            },
        })
        self.assertEqual(r.status, Decision.SUPPORTED)
    def test_fsdp2_qlora_on_old_accelerate_requires_canary(self):
        r = evaluate_profile({
            "profile_id": "p",
            "peft": {"qlora_4bit": True},
            "hardware": {"gpu": True},
            "packages": {"bitsandbytes": "0.48.2", "accelerate": "1.13.0"},
            "distributed": {"fsdp_version": 2},
        })
        self.assertEqual(r.status, Decision.NEEDS_CANARY)
        self.assertIn("fsdp2_qlora_compatibility", r.canaries)

    def test_fsdp2_qlora_on_accelerate_1_14_is_supported(self):
        r = evaluate_profile({
            "profile_id": "p",
            "peft": {"qlora_4bit": True},
            "hardware": {"gpu": True},
            "packages": {"bitsandbytes": "0.48.2", "accelerate": "1.14.0"},
            "distributed": {"fsdp_version": 2},
        })
        self.assertEqual(r.status, Decision.SUPPORTED)


if __name__ == "__main__":
    unittest.main()

class TransformersUntrustedIntakeTests(unittest.TestCase):
    def test_untrusted_transformers_repo_requires_sandbox(self):
        r = evaluate_profile({
            "profile_id": "p",
            "transformers": {"untrusted_repo": True, "revision_pinned": True, "sandboxed": False},
        })
        self.assertEqual(r.status, Decision.UNSUPPORTED)
        self.assertIn("transformers.untrusted_repo.sandbox", r.rules)

    def test_untrusted_transformers_repo_requires_pinned_revision(self):
        r = evaluate_profile({
            "profile_id": "p",
            "transformers": {"untrusted_repo": True, "revision_pinned": False, "sandboxed": True},
        })
        self.assertEqual(r.status, Decision.UNSUPPORTED)
        self.assertIn("transformers.untrusted_repo.revision_pin", r.rules)

    def test_quarantined_pinned_untrusted_repo_can_continue(self):
        r = evaluate_profile({
            "profile_id": "p",
            "transformers": {"untrusted_repo": True, "revision_pinned": True, "sandboxed": True},
        })
        self.assertEqual(r.status, Decision.SUPPORTED)
