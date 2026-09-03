import unittest

from projects.ultratrain.compatibility_core import Decision, evaluate_profile


class PyTorch214CompatibilityTests(unittest.TestCase):
    def test_nccl2_requires_pytorch_214(self):
        result = evaluate_profile({
            "profile_id": "p",
            "packages": {"torch": "2.13.0"},
            "distributed": {"backend": "nccl2"},
        })
        self.assertEqual(result.status, Decision.UNSUPPORTED)

    def test_nccl2_is_supported_on_pytorch_214(self):
        result = evaluate_profile({
            "profile_id": "p",
            "packages": {"torch": "2.14.0"},
            "distributed": {"backend": "nccl2"},
        })
        self.assertEqual(result.status, Decision.SUPPORTED)

    def test_fault_tolerant_reconfiguration_requires_pytorch_214(self):
        result = evaluate_profile({
            "profile_id": "p",
            "packages": {"torch": "2.13.0"},
            "distributed": {"fault_tolerant_reconfiguration": True},
        })
        self.assertEqual(result.status, Decision.UNSUPPORTED)

    def test_fault_tolerant_reconfiguration_supported_on_214(self):
        result = evaluate_profile({
            "profile_id": "p",
            "packages": {"torch": "2.14.0"},
            "distributed": {"fault_tolerant_reconfiguration": True},
        })
        self.assertEqual(result.status, Decision.SUPPORTED)

    def test_new_distributed_capability_without_torch_identity_needs_canary(self):
        result = evaluate_profile({
            "profile_id": "p",
            "distributed": {"backend": "nccl2"},
        })
        self.assertEqual(result.status, Decision.NEEDS_CANARY)
        self.assertEqual(result.canaries, ("pytorch_214_capability_identity",))

    def test_invalid_torch_version_needs_canary(self):
        result = evaluate_profile({
            "profile_id": "p",
            "packages": {"torch": "nightly"},
            "distributed": {"fault_tolerant_reconfiguration": True},
        })
        self.assertEqual(result.status, Decision.NEEDS_CANARY)


if __name__ == "__main__":
    unittest.main()
