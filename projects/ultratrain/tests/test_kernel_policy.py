import unittest

from projects.ultratrain.kernel_policy import KernelStatus, route_kernel


class KernelPolicyTests(unittest.TestCase):
    def test_sdpa_is_default(self):
        result = route_kernel({})
        self.assertEqual(result.status, KernelStatus.SUPPORTED)
        self.assertEqual(result.backend, "sdpa")

    def test_liger_auto_promotes_only_after_canary(self):
        result = route_kernel({
            "prefer_fused_kernels": True,
            "liger_available": True,
            "liger_canary_passed": True,
        })
        self.assertEqual(result.backend, "liger")

    def test_unverified_auto_liger_stays_on_sdpa(self):
        result = route_kernel({
            "prefer_fused_kernels": True,
            "liger_available": True,
            "liger_canary_passed": False,
        })
        self.assertEqual(result.status, KernelStatus.SUPPORTED)
        self.assertEqual(result.backend, "sdpa")
        self.assertIn("kernel.liger_not_promoted_without_canary", result.decisions)

    def test_explicit_unverified_liger_requires_canary(self):
        result = route_kernel({
            "kernel_preference": "liger",
            "liger_available": True,
            "liger_canary_passed": False,
        })
        self.assertEqual(result.backend, "liger")
        self.assertEqual(result.status, KernelStatus.NEEDS_CANARY)
        self.assertIn("liger_correctness", result.canaries)


if __name__ == "__main__":
    unittest.main()
