import json
import unittest

from projects.ultratrain.hardware_doctor_contract import (
    CapabilityEvidence,
    CapabilityState,
    HardwareSnapshot,
    MemoryEstimate,
    ModelCapabilityProfile,
    PackageIdentity,
    PlannerCapabilityInput,
    RuntimeProviderDescriptor,
)


class HardwareDoctorContractTests(unittest.TestCase):
    def test_package_identity_requires_exact_name_and_version(self):
        with self.assertRaises(ValueError):
            PackageIdentity(name="trl", version="")
        item = PackageIdentity(name="trl", version="1.13.0", source="installed")
        self.assertEqual(item.version, "1.13.0")

    def test_package_presence_never_implies_capability(self):
        runtime = RuntimeProviderDescriptor(
            provider_id="canonical",
            isolation="shared",
            packages=(PackageIdentity("liger-kernel", "0.8.2"),),
        )
        self.assertEqual(runtime.capability_state("liger.preference_frozen_weight_fastpath"), CapabilityState.UNKNOWN)

    def test_conflicting_runtime_must_be_isolated(self):
        with self.assertRaises(ValueError):
            RuntimeProviderDescriptor(
                provider_id="unsloth-2026.9.4",
                isolation="shared",
                packages=(PackageIdentity("trl", "0.23.1"),),
                conflicts=("canonical:trl>=1.13.0",),
            )
        runtime = RuntimeProviderDescriptor(
            provider_id="unsloth-2026.9.4",
            isolation="process",
            packages=(
                PackageIdentity("unsloth", "2026.9.4"),
                PackageIdentity("trl", "0.23.1"),
                PackageIdentity("transformers", "5.5.0"),
            ),
            conflicts=("canonical:trl>=1.13.0", "canonical:transformers>=5.16"),
        )
        self.assertTrue(runtime.requires_isolation)

    def test_memory_estimate_preserves_evidence_and_uncertainty(self):
        estimate = MemoryEstimate(
            bytes_required=16_074_530_924,
            basis="estimated",
            confidence=0.65,
            assumptions=("mlx-4bit-weight-payload", "kv-cache-not-included"),
        )
        self.assertEqual(estimate.basis, "estimated")
        self.assertLess(estimate.confidence, 1.0)
        self.assertIn("kv-cache-not-included", estimate.assumptions)

    def test_model_profile_is_baseline_plus_deltas(self):
        model = ModelCapabilityProfile(
            model_id="Qwen/Qwen3.8-27B",
            family="qwen3_5",
            baseline={"modalities": ["text"], "max_context": 262144},
            deltas={"modalities": ["text", "image", "video"], "tool_calls": True, "thinking": True},
        )
        resolved = model.resolved_capabilities()
        self.assertEqual(resolved["modalities"], ["text", "image", "video"])
        self.assertTrue(resolved["tool_calls"])
        self.assertEqual(resolved["max_context"], 262144)

    def test_qwen_profile_does_not_claim_safe_autonomous_tools(self):
        model = ModelCapabilityProfile(
            model_id="Qwen3.8-27B-Uncensored-MLX",
            family="qwen3_5",
            baseline={"tool_calls": True},
            deltas={"refusal_behavior_modified": True},
        )
        self.assertNotIn("safe_autonomous_tools", model.resolved_capabilities())

    def test_capability_requires_explicit_evidence(self):
        runtime = RuntimeProviderDescriptor(
            provider_id="canonical",
            isolation="shared",
            capabilities=(
                CapabilityEvidence(
                    capability="attention.sdpa",
                    state=CapabilityState.PROBED,
                    evidence="hardware-doctor:sdpa-smoke",
                ),
            ),
        )
        self.assertEqual(runtime.capability_state("attention.sdpa"), CapabilityState.PROBED)
        self.assertEqual(runtime.capability_state("attention.flash_attention_4"), CapabilityState.UNKNOWN)

    def test_planner_input_has_stable_json_contract(self):
        payload = PlannerCapabilityInput(
            schema_version="ultratrain.hardware_capability/v1",
            runtime=RuntimeProviderDescriptor(provider_id="canonical", isolation="shared"),
            hardware=HardwareSnapshot(platform="linux", ram_bytes=64 * 1024**3),
            model=ModelCapabilityProfile(model_id="fixture/model", family="fixture"),
            memory=MemoryEstimate(bytes_required=1024, basis="measured", confidence=1.0),
        )
        first = payload.to_json()
        second = payload.to_json()
        self.assertEqual(first, second)
        decoded = json.loads(first)
        self.assertEqual(decoded["schema_version"], "ultratrain.hardware_capability/v1")
        self.assertEqual(decoded["runtime"]["provider_id"], "canonical")


if __name__ == "__main__":
    unittest.main()
