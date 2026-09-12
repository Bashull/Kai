import unittest

from projects.ultratrain.weight_delta_policy import WeightDeltaStatus, select_weight_delta_transport


class WeightDeltaPolicyTests(unittest.TestCase):
    def test_vllm_029_prefers_sharded_rdt_when_capability_and_canary_are_present(self):
        result = select_weight_delta_transport({
            "vllm_version": "0.29.0",
            "tensor_parallel_size": 4,
            "expert_parallel_size": 2,
            "sharded_rdt_available": True,
            "sharded_rdt_canary_passed": True,
        })
        self.assertEqual(result.transport, "sharded_rdt")
        self.assertEqual(result.status, WeightDeltaStatus.SUPPORTED)
        self.assertIn("weight_delta.vllm029.sharded_rdt", result.decisions)

    def test_sharded_rdt_requires_canary_before_promotion(self):
        result = select_weight_delta_transport({
            "vllm_version": "0.29.0",
            "tensor_parallel_size": 2,
            "sharded_rdt_available": True,
        })
        self.assertEqual(result.transport, "sharded_rdt")
        self.assertEqual(result.status, WeightDeltaStatus.NEEDS_CANARY)
        self.assertIn("vllm_sharded_rdt_weight_sync", result.canaries)

    def test_pre_029_does_not_claim_sharded_rdt(self):
        result = select_weight_delta_transport({
            "vllm_version": "0.28.0",
            "sharded_rdt_available": True,
            "sharded_rdt_canary_passed": True,
        })
        self.assertNotEqual(result.transport, "sharded_rdt")

    def test_sparse_nccl_requires_explicit_capability(self):
        result = select_weight_delta_transport({
            "vllm_version": "0.29.0",
            "sparse_nccl_available": True,
            "sparse_nccl_canary_passed": True,
        })
        self.assertEqual(result.transport, "sparse_nccl")
        self.assertEqual(result.status, WeightDeltaStatus.SUPPORTED)

    def test_safe_default_is_full_nccl_when_advanced_capabilities_are_unknown(self):
        result = select_weight_delta_transport({"vllm_version": "0.29.0"})
        self.assertEqual(result.transport, "full_nccl")
        self.assertEqual(result.status, WeightDeltaStatus.SUPPORTED)


if __name__ == "__main__":
    unittest.main()
