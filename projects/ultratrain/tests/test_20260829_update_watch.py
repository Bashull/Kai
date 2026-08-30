import unittest

from projects.ultratrain.compatibility_core import Decision, evaluate_profile


class UpdateWatch20260829SupersededTests(unittest.TestCase):
    def test_vllm_0271_specific_canaries_are_superseded_by_028_security_floor(self):
        r = evaluate_profile({
            "profile_id": "p",
            "peft": {"lora": True},
            "packages": {"mcp": "2.0.0"},
            "runtime": {
                "vllm": True,
                "vllm_version": "0.27.1",
                "vllm_canary_passed": True,
                "vllm_sleep_level": 1,
                "post_wake_determinism_canary_passed": True,
                "vllm_tool_server": True,
            },
        })
        self.assertEqual(r.status, Decision.UNSUPPORTED)
        self.assertIn("runtime.vllm.security_floor_028", r.rules)


if __name__ == "__main__":
    unittest.main()
