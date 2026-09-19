import unittest

from projects.ultratrain.sglang_security_policy import (
    SGLangSecurityStatus,
    evaluate_sglang_security,
)


class SGLangSecurityPolicyTests(unittest.TestCase):
    def test_non_sglang_runtime_is_out_of_scope(self):
        result = evaluate_sglang_security({"runtime_provider": "vllm"})
        self.assertEqual(result.status, SGLangSecurityStatus.SUPPORTED)

    def test_sglang_without_pd_is_not_affected_by_this_gate(self):
        result = evaluate_sglang_security({"runtime_provider": "sglang", "pd_disaggregation": False})
        self.assertEqual(result.status, SGLangSecurityStatus.SUPPORTED)

    def test_public_rank_port_is_blocked(self):
        result = evaluate_sglang_security({
            "runtime_provider": "sglang",
            "pd_disaggregation": True,
            "sglang_zmq_rank_port_exposure": "public",
        })
        self.assertEqual(result.status, SGLangSecurityStatus.UNSUPPORTED)
        self.assertIn("security.sglang.cve_2026_93838.rank_port_untrusted", result.rules)

    def test_trusted_only_rank_port_is_allowed_as_compensating_control(self):
        result = evaluate_sglang_security({
            "runtime_provider": "sglang",
            "pd_disaggregation": True,
            "sglang_zmq_rank_port_exposure": "trusted_only",
        })
        self.assertEqual(result.status, SGLangSecurityStatus.SUPPORTED)
        self.assertIn("security.sglang.cve_2026_93838.network_isolated", result.decisions)

    def test_unknown_exposure_requires_probe(self):
        result = evaluate_sglang_security({
            "runtime_provider": "sglang",
            "pd_disaggregation": True,
        })
        self.assertEqual(result.status, SGLangSecurityStatus.NEEDS_CANARY)
        self.assertIn("sglang_pd_zmq_rank_port_exposure", result.canaries)


if __name__ == "__main__":
    unittest.main()
