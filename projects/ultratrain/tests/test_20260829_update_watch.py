import unittest

from projects.ultratrain.compatibility_core import Decision, evaluate_profile


class UpdateWatch20260829Tests(unittest.TestCase):
    def test_vllm_0271_lora_sleep_level1_requires_post_wake_canary(self):
        r = evaluate_profile({
            "profile_id": "p",
            "peft": {"lora": True},
            "runtime": {
                "vllm": True,
                "vllm_version": "0.27.1",
                "vllm_canary_passed": True,
                "vllm_sleep_level": 1,
            },
        })
        self.assertEqual(r.status, Decision.NEEDS_CANARY)
        self.assertIn("vllm_lora_sleep_wake", r.canaries)

    def test_vllm_0271_lora_sleep_level1_passes_with_determinism_canary(self):
        r = evaluate_profile({
            "profile_id": "p",
            "peft": {"lora": True},
            "runtime": {
                "vllm": True,
                "vllm_version": "0.27.1",
                "vllm_canary_passed": True,
                "vllm_sleep_level": 1,
                "post_wake_determinism_canary_passed": True,
            },
        })
        self.assertEqual(r.status, Decision.SUPPORTED)

    def test_vllm_0271_mcp2_tool_server_is_unsupported(self):
        r = evaluate_profile({
            "profile_id": "p",
            "packages": {"mcp": "2.0.0"},
            "runtime": {
                "vllm": True,
                "vllm_version": "0.27.1",
                "vllm_canary_passed": True,
                "vllm_tool_server": True,
            },
        })
        self.assertEqual(r.status, Decision.UNSUPPORTED)
        self.assertIn("runtime.vllm.mcp2_incompatible", r.rules)


if __name__ == "__main__":
    unittest.main()
