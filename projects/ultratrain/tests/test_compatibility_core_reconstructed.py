import json
import unittest

from projects.ultratrain.compatibility_core import Decision, evaluate_profile


class ReconstructedCompatibilityContractTests(unittest.TestCase):
    def test_identity_is_required(self):
        r = evaluate_profile({})
        self.assertEqual(r.status, Decision.UNSUPPORTED)

    def test_minimal_transformers_profile_is_supported(self):
        r = evaluate_profile({"profile_id": "p1", "transformers": {}})
        self.assertEqual(r.status, Decision.SUPPORTED)

    def test_qlora_4bit_requires_gpu(self):
        r = evaluate_profile({"profile_id": "p", "peft": {"qlora_4bit": True}, "hardware": {"gpu": False}})
        self.assertEqual(r.status, Decision.UNSUPPORTED)

    def test_qlora_4bit_requires_bitsandbytes(self):
        r = evaluate_profile({"profile_id": "p", "peft": {"qlora_4bit": True}, "hardware": {"gpu": True}})
        self.assertEqual(r.status, Decision.UNSUPPORTED)

    def test_qlora_4bit_supported_with_requirements(self):
        r = evaluate_profile({"profile_id": "p", "peft": {"qlora_4bit": True}, "hardware": {"gpu": True}, "packages": {"bitsandbytes": "1"}})
        self.assertEqual(r.status, Decision.SUPPORTED)

    def test_multinode_geometry_requires_positive_nodes(self):
        r = evaluate_profile({"profile_id": "p", "distributed": {"nodes": 0}})
        self.assertEqual(r.status, Decision.UNSUPPORTED)

    def test_ray_requires_explicit_enablement(self):
        r = evaluate_profile({"profile_id": "p", "ray": {"requested": True, "enabled": False}})
        self.assertEqual(r.status, Decision.UNSUPPORTED)

    def test_dataset_schema_mismatch_is_unsupported(self):
        r = evaluate_profile({"profile_id": "p", "dataset": {"schema_valid": False}})
        self.assertEqual(r.status, Decision.UNSUPPORTED)

    def test_merge_is_required_before_gguf_for_lora(self):
        r = evaluate_profile({"profile_id": "p", "peft": {"lora": True, "merged": False}, "export": {"target": "gguf"}})
        self.assertEqual(r.status, Decision.UNSUPPORTED)

    def test_converter_identity_is_required_for_gguf(self):
        r = evaluate_profile({"profile_id": "p", "export": {"target": "gguf"}})
        self.assertEqual(r.status, Decision.NEEDS_CANARY)

    def test_xet_without_canary_blocks(self):
        r = evaluate_profile({"profile_id": "p", "hub": {"xet": True}})
        self.assertEqual(r.status, Decision.NEEDS_CANARY)

    def test_vllm_without_canary_blocks(self):
        r = evaluate_profile({"profile_id": "p", "runtime": {"vllm": True}})
        self.assertEqual(r.status, Decision.NEEDS_CANARY)

    def test_report_serializes_and_needs_canary_disallows_continue(self):
        r = evaluate_profile({"profile_id": "p", "runtime": {"vllm": True}})
        payload = json.loads(r.to_json())
        self.assertEqual(payload["status"], "NEEDS_CANARY")
        self.assertFalse(payload["allow_continue"])


if __name__ == "__main__":
    unittest.main()
