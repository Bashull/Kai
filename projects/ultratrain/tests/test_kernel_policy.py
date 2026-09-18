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

    def test_verified_cutedsl_backend_is_exposed_as_capability(self):
        result = route_kernel({
            "kernel_preference": "liger",
            "liger_available": True,
            "liger_version": "0.8.3",
            "liger_canary_passed": True,
            "liger_dsl_backend": "cutedsl",
            "liger_dsl_backend_available": True,
            "liger_dsl_canary_passed": True,
        })
        self.assertIn("kernel.liger.dsl.cutedsl_verified", result.decisions)

    def test_dsl_backend_is_not_promoted_without_083_and_canary(self):
        result = route_kernel({
            "kernel_preference": "liger",
            "liger_available": True,
            "liger_version": "0.8.2",
            "liger_canary_passed": True,
            "liger_dsl_backend": "cutedsl",
            "liger_dsl_backend_available": True,
            "liger_dsl_canary_passed": True,
        })
        self.assertNotIn("kernel.liger.dsl.cutedsl_verified", result.decisions)

    def test_distillation_fused_linear_kl_is_exposed_only_with_verified_capability(self):
        result = route_kernel({
            "method": "distillation",
            "kernel_preference": "liger",
            "liger_available": True,
            "liger_version": "0.8.3",
            "liger_canary_passed": True,
            "liger_fused_linear_kl_available": True,
            "liger_fused_linear_kl_canary_passed": True,
        })
        self.assertIn("kernel.liger.distillation.fused_linear_kl_verified", result.decisions)

    def test_distillation_fused_linear_kl_is_not_inferred_from_version(self):
        result = route_kernel({
            "method": "distillation",
            "kernel_preference": "liger",
            "liger_available": True,
            "liger_version": "0.8.3",
            "liger_canary_passed": True,
        })
        self.assertNotIn("kernel.liger.distillation.fused_linear_kl_verified", result.decisions)


if __name__ == "__main__":
    unittest.main()
