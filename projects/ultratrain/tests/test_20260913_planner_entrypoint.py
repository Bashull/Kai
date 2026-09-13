import unittest

from projects.ultratrain.hardware_doctor_contract import (
    HardwareSnapshot,
    ModelCapabilityProfile,
    PackageIdentity,
    PlannerCapabilityInput,
    RuntimeProviderDescriptor,
)
from projects.ultratrain.planner_entrypoint import plan_training_with_capabilities


class PlannerEntrypointTests(unittest.TestCase):
    def _capability_input(self):
        return PlannerCapabilityInput(
            schema_version="ultratrain.hardware_capability/v1",
            runtime=RuntimeProviderDescriptor(
                provider_id="canonical",
                isolation="shared",
                packages=(PackageIdentity("trl", "1.13.0"),),
            ),
            hardware=HardwareSnapshot(platform="linux", ram_bytes=32 * 1024**3),
            model=ModelCapabilityProfile(model_id="fixture/model", family="fixture"),
        )

    def test_entrypoint_delegates_enriched_copy_to_planner(self):
        seen = {}

        def fake_planner(request):
            seen.update(request)
            return "planned"

        original = {"profile_id": "fixture", "method": "sft"}
        result = plan_training_with_capabilities(
            original,
            self._capability_input(),
            planner=fake_planner,
        )
        self.assertEqual(result, "planned")
        self.assertEqual(seen["trl_version"], "1.13.0")
        self.assertEqual(seen["capability_runtime"]["provider_id"], "canonical")
        self.assertNotIn("trl_version", original)

    def test_entrypoint_preserves_explicit_preferences(self):
        seen = {}

        def fake_planner(request):
            seen.update(request)
            return request

        plan_training_with_capabilities(
            {"kernel_preference": "sdpa"},
            self._capability_input(),
            planner=fake_planner,
        )
        self.assertEqual(seen["kernel_preference"], "sdpa")


if __name__ == "__main__":
    unittest.main()
