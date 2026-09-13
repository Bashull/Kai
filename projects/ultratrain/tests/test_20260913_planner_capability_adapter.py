import copy
import unittest

from projects.ultratrain.hardware_doctor_contract import (
    CapabilityEvidence,
    CapabilityState,
    GPUDevice,
    HardwareSnapshot,
    MemoryEstimate,
    ModelCapabilityProfile,
    PackageIdentity,
    PlannerCapabilityInput,
    RuntimeProviderDescriptor,
)
from projects.ultratrain.planner_capability_adapter import (
    CapabilityInputConflict,
    adapt_training_request,
)


def _input(*, capabilities=(), packages=(), model=None, gpus=(), isolation="shared", conflicts=()):
    return PlannerCapabilityInput(
        schema_version="ultratrain.hardware_capability/v1",
        runtime=RuntimeProviderDescriptor(
            provider_id="fixture-runtime",
            isolation=isolation,
            packages=tuple(packages),
            capabilities=tuple(capabilities),
            conflicts=tuple(conflicts),
        ),
        hardware=HardwareSnapshot(
            platform="linux",
            ram_bytes=64 * 1024**3,
            cpu="fixture",
            gpus=tuple(gpus),
        ),
        model=model or ModelCapabilityProfile(model_id="fixture/model", family="fixture"),
        memory=MemoryEstimate(bytes_required=1234, basis="estimated", confidence=0.5),
    )


class PlannerCapabilityAdapterTests(unittest.TestCase):
    def test_request_is_not_mutated(self):
        request = {"profile_id": "x", "packages": {"torch": "2.14.0"}}
        original = copy.deepcopy(request)
        adapt_training_request(request, _input())
        self.assertEqual(request, original)

    def test_exact_package_identity_is_mapped(self):
        adapted = adapt_training_request(
            {"profile_id": "x"},
            _input(packages=(
                PackageIdentity("trl", "1.13.0"),
                PackageIdentity("transformers", "5.16.0"),
                PackageIdentity("accelerate", "1.12.0"),
            )),
        )
        self.assertEqual(adapted["packages"]["trl"], "1.13.0")
        self.assertEqual(adapted["trl_version"], "1.13.0")
        self.assertEqual(adapted["transformers_version"], "5.16.0")
        self.assertEqual(adapted["accelerate"], "1.12.0")

    def test_conflicting_factual_package_identity_is_rejected(self):
        with self.assertRaises(CapabilityInputConflict):
            adapt_training_request(
                {"packages": {"trl": "1.12.0"}},
                _input(packages=(PackageIdentity("trl", "1.13.0"),)),
            )

    def test_hardware_gpu_fact_is_mapped(self):
        adapted = adapt_training_request(
            {},
            _input(gpus=(GPUDevice(0, "RTX", 24 * 1024**3),)),
        )
        self.assertTrue(adapted["hardware"]["gpu"])
        self.assertEqual(adapted["hardware"]["gpu_count"], 1)
        self.assertEqual(adapted["hardware"]["vram_bytes"], [24 * 1024**3])

    def test_explicit_user_kernel_preference_is_preserved(self):
        adapted = adapt_training_request(
            {"kernel_preference": "sdpa"},
            _input(capabilities=(
                CapabilityEvidence("kernel.liger", CapabilityState.CANARY, "canary:liger"),
            )),
        )
        self.assertEqual(adapted["kernel_preference"], "sdpa")
        self.assertTrue(adapted["liger_available"])
        self.assertTrue(adapted["liger_canary_passed"])

    def test_unknown_or_declared_liger_does_not_auto_promote(self):
        adapted = adapt_training_request(
            {},
            _input(capabilities=(
                CapabilityEvidence("kernel.liger", CapabilityState.DECLARED, "upstream-doc"),
            )),
        )
        self.assertNotIn("liger_available", adapted)
        self.assertNotIn("liger_canary_passed", adapted)

    def test_probed_liger_marks_available_but_not_canary_passed(self):
        adapted = adapt_training_request(
            {},
            _input(capabilities=(
                CapabilityEvidence("kernel.liger", CapabilityState.PROBED, "probe:import+smoke"),
            )),
        )
        self.assertTrue(adapted["liger_available"])
        self.assertNotIn("liger_canary_passed", adapted)

    def test_model_context_parallel_is_only_mapped_when_declared(self):
        with_cp = ModelCapabilityProfile(
            model_id="fixture/model",
            family="fixture",
            deltas={"supports_context_parallel": False, "kv_heads": 4, "max_context": 262144},
        )
        adapted = adapt_training_request({}, _input(model=with_cp))
        self.assertIs(adapted["model_supports_context_parallel"], False)
        self.assertEqual(adapted["kv_heads"], 4)
        self.assertEqual(adapted["native_context_tokens"], 262144)

        unknown = adapt_training_request({}, _input())
        self.assertNotIn("model_supports_context_parallel", unknown)

    def test_only_probed_attention_backend_is_auto_selected(self):
        declared = adapt_training_request(
            {},
            _input(capabilities=(
                CapabilityEvidence("attention.sdpa", CapabilityState.DECLARED, "docs"),
            )),
        )
        self.assertNotIn("attention", declared)

        probed = adapt_training_request(
            {},
            _input(capabilities=(
                CapabilityEvidence("attention.sdpa", CapabilityState.PROBED, "probe:sdpa"),
            )),
        )
        self.assertEqual(probed["attention"], "sdpa")

    def test_runtime_isolation_and_memory_provenance_are_preserved(self):
        adapted = adapt_training_request(
            {},
            _input(isolation="process", conflicts=("canonical:trl>=1.13.0",)),
        )
        self.assertEqual(adapted["capability_runtime"]["provider_id"], "fixture-runtime")
        self.assertEqual(adapted["capability_runtime"]["isolation"], "process")
        self.assertEqual(adapted["memory_estimate"]["bytes_required"], 1234)


if __name__ == "__main__":
    unittest.main()
