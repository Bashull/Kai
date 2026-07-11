from __future__ import annotations

import json
import os
import subprocess
import sys
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




class CapabilityRegistryCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = Path(__file__).resolve().parents[1] / "tools" / "kai_capability_registry.py"

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.tool), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            check=False,
        )

    def test_register_manifest_transition_and_doctor_cli(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "registry"
            candidate_file = root / "candidate.json"
            candidate_file.write_text(json.dumps({
                "name": "kai_mapper.py",
                "sha256": "b" * 64,
                "decision": "TOOL_CANDIDATE",
                "capabilities": ["repository_mapping"],
                "secret_signals": [],
                "provenance": {"source_type": "LOCAL_FILE", "source": "C:/evidence/kai_mapper.py"},
            }), encoding="utf-8")

            registered = self.run_cli("register", "--home", str(home), "--candidate", str(candidate_file))
            self.assertEqual(registered.returncode, 0, registered.stderr)
            capability_id = json.loads(registered.stdout)["capability_id"]

            evidence_file = root / "evidence.json"
            evidence_file.write_text(json.dumps({"classification": "tool"}), encoding="utf-8")
            transitioned = self.run_cli("transition", "--home", str(home), "--capability-id", capability_id, "--state", "CLASSIFIED", "--evidence", str(evidence_file))
            self.assertEqual(transitioned.returncode, 0, transitioned.stderr)
            self.assertEqual(json.loads(transitioned.stdout)["state"], "CLASSIFIED")

            manifest = self.run_cli("manifest", "--home", str(home))
            self.assertEqual(manifest.returncode, 0, manifest.stderr)
            self.assertEqual(json.loads(manifest.stdout)[0]["state"], "CLASSIFIED")

            doctor = self.run_cli("doctor", "--home", str(home))
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            diagnosis = json.loads(doctor.stdout)
            self.assertEqual(diagnosis["status"], "HEALTHY")
            self.assertEqual(diagnosis["capability_count"], 1)

if __name__ == "__main__":
    unittest.main()
