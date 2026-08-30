import unittest

from projects.ultratrain.compatibility_core import Decision, evaluate_profile


class UpdateWatch20260830Tests(unittest.TestCase):
    def test_vllm_before_028_is_unsupported_after_remote_code_advisory(self):
        r = evaluate_profile({"profile_id": "p", "runtime": {"vllm": True, "vllm_version": "0.27.1", "vllm_canary_passed": True}})
        self.assertEqual(r.status, Decision.UNSUPPORTED)
        self.assertIn("runtime.vllm.security_floor_028", r.rules)

    def test_vllm_028_can_continue_after_runtime_canary(self):
        r = evaluate_profile({"profile_id": "p", "runtime": {"vllm": True, "vllm_version": "0.28.0", "vllm_canary_passed": True}})
        self.assertEqual(r.status, Decision.SUPPORTED)

    def test_sglang_gptq_marlin_moe_bf16_tp_requires_canary(self):
        r = evaluate_profile({"profile_id": "p", "runtime": {"sglang": True, "sglang_gptq_marlin_moe": True, "dtype": "bfloat16", "tensor_parallel_size": 2}})
        self.assertEqual(r.status, Decision.NEEDS_CANARY)
        self.assertIn("sglang_gptq_marlin_moe_tp", r.canaries)


if __name__ == "__main__":
    unittest.main()
