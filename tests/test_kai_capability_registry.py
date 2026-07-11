from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.kai_capability_registry import CapabilityRegistry


class CapabilityRegistryTests(unittest.TestCase):
    def candidate(self) -> dict:
        return {
            "name": "kai_mapper.py",
            "sha256": "a" * 64,
            "decision": "TOOL_CANDIDATE",
            "capabilities": ["repository_mapping", "memory"],
            "secret_signals": [],
            "provenance": {
                "source_type": "LOCAL_FILE",
                "source": "C:/evidence/kai_mapper.py",
            },
        }

    def test_registration_is_persistent_and_idempotent(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            registry = CapabilityRegistry(home)
            first = registry.register(self.candidate())
            second = registry.register(self.candidate())
            self.assertEqual(first["decision"], "REGISTERED")
            self.assertEqual(second["decision"], "SKIP_EXACT_DUPLICATE")
            reopened = CapabilityRegistry(home)
            manifest = reopened.current_manifest()
            self.assertEqual(len(manifest), 1)
            self.assertEqual(manifest[0]["state"], "DISCOVERED")

    def test_invalid_state_jump_is_rejected(self):
        with TemporaryDirectory() as tmp:
            registry = CapabilityRegistry(Path(tmp))
            capability_id = registry.register(self.candidate())["capability_id"]
            with self.assertRaises(ValueError):
                registry.transition(capability_id, "PROMOTED", {"reason": "too soon"})

    def test_validation_requires_passing_test_evidence(self):
        with TemporaryDirectory() as tmp:
            registry = CapabilityRegistry(Path(tmp))
            capability_id = registry.register(self.candidate())["capability_id"]
            registry.transition(capability_id, "CLASSIFIED", {"classification": "tool"})
            registry.transition(capability_id, "CANDIDATE", {"reviewed": True})
            registry.transition(capability_id, "TESTING", {"suite": "unit"})
            with self.assertRaises(ValueError):
                registry.transition(capability_id, "VALIDATED", {"reviewed": True})
            result = registry.transition(
                capability_id,
                "VALIDATED",
                {"tests": {"passed": 4, "failed": 0}},
            )
            self.assertEqual(result["state"], "VALIDATED")

    def test_canonical_requires_explicit_approval(self):
        with TemporaryDirectory() as tmp:
            registry = CapabilityRegistry(Path(tmp))
            capability_id = registry.register(self.candidate())["capability_id"]
            registry.transition(capability_id, "CLASSIFIED", {"classification": "tool"})
            registry.transition(capability_id, "CANDIDATE", {"reviewed": True})
            registry.transition(capability_id, "TESTING", {"suite": "unit"})
            registry.transition(capability_id, "VALIDATED", {"tests": {"passed": 4, "failed": 0}})
            registry.transition(capability_id, "PROMOTED", {"deployment": "bridge"})
            with self.assertRaises(ValueError):
                registry.transition(capability_id, "CANONICAL", {"explicit_approval": False})
            result = registry.transition(capability_id, "CANONICAL", {"explicit_approval": True})
            self.assertEqual(result["state"], "CANONICAL")


if __name__ == "__main__":
    unittest.main()
