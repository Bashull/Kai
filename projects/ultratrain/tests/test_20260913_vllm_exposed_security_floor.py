import unittest

from projects.ultratrain.compatibility_core import Decision, evaluate_profile


class VllmExposedSecurityFloorTests(unittest.TestCase):
    def _profile(self, version: str, **runtime_overrides):
        runtime = {
            "vllm": True,
            "vllm_version": version,
            "vllm_canary_passed": True,
        }
        runtime.update(runtime_overrides)
        return {
            "profile_id": "vllm-security-floor",
            "runtime": runtime,
        }

    def test_local_isolated_vllm_028_remains_supported(self):
        result = evaluate_profile(self._profile("0.28.0", network_exposure="local"))
        self.assertEqual(result.status, Decision.SUPPORTED)

    def test_lan_exposed_vllm_028_is_rejected(self):
        result = evaluate_profile(self._profile("0.28.0", network_exposure="lan"))
        self.assertEqual(result.status, Decision.UNSUPPORTED)
        self.assertIn("runtime.vllm.exposed_security_floor_029", result.rules)

    def test_public_vllm_028_is_rejected(self):
        result = evaluate_profile(self._profile("0.28.0", network_exposure="public"))
        self.assertEqual(result.status, Decision.UNSUPPORTED)
        self.assertIn("runtime.vllm.exposed_security_floor_029", result.rules)

    def test_tool_server_vllm_028_is_rejected_even_when_local(self):
        result = evaluate_profile(self._profile("0.28.0", network_exposure="local", vllm_tool_server=True))
        self.assertEqual(result.status, Decision.UNSUPPORTED)
        self.assertIn("runtime.vllm.exposed_security_floor_029", result.rules)

    def test_exposed_vllm_029_is_allowed_after_runtime_canary(self):
        result = evaluate_profile(self._profile("0.29.0", network_exposure="public"))
        self.assertEqual(result.status, Decision.SUPPORTED)


if __name__ == "__main__":
    unittest.main()
