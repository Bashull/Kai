from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.kai_capability_scanner import scan_artifact, sha256_file


class CapabilityScannerTests(unittest.TestCase):
    def test_python_tool_candidate_extracts_structure_and_capabilities(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "kai_memory_mapper.py"
            path.write_text(
                "import json\nfrom pathlib import Path\n\n"
                "class Mapper:\n    pass\n\n"
                "def map_repository(root: Path):\n    return {'memory': str(root)}\n",
                encoding="utf-8",
            )
            result = scan_artifact(path)
            self.assertEqual(result["decision"], "TOOL_CANDIDATE")
            self.assertEqual(result["artifact_type"], "CODE")
            self.assertEqual(len(result["sha256"]), 64)
            self.assertIn("Mapper", result["structure"]["classes"])
            self.assertIn("map_repository", result["structure"]["functions"])
            self.assertIn("memory", result["capabilities"])
            self.assertIn("repository_mapping", result["capabilities"])

    def test_known_sha256_is_exact_duplicate(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.txt"
            path.write_text("same bytes", encoding="utf-8")
            digest = sha256_file(path)
            result = scan_artifact(path, known_hashes={digest})
            self.assertEqual(result["decision"], "DUPLICATE")
            self.assertEqual(result["duplicate_basis"], "SHA256_EXACT")

    def test_secret_signal_quarantines_without_emitting_secret_value(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "client_secret.json"
            secret_value = "synthetic-secret-value-123456789"
            path.write_text(
                json.dumps({"client_secret": secret_value, "project": "kai"}),
                encoding="utf-8",
            )
            result = scan_artifact(path)
            rendered = json.dumps(result, ensure_ascii=False)
            self.assertEqual(result["decision"], "QUARANTINED")
            self.assertTrue(result["secret_signals"])
            self.assertNotIn(secret_value, rendered)

    def test_protocol_document_becomes_protocol_candidate(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "RESTORE_PROTOCOL.md"
            path.write_text(
                "# Restoration Protocol\nDirective: preserve provenance and rollback before promotion.\n",
                encoding="utf-8",
            )
            result = scan_artifact(path)
            self.assertEqual(result["decision"], "PROTOCOL_CANDIDATE")
            self.assertIn("governance_protocols", result["capabilities"])




class CapabilityScannerCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = Path(__file__).resolve().parents[1] / "tools" / "kai_capability_scanner.py"

    def test_scan_cli_writes_json_output(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "kai_mapper.py"
            artifact.write_text("def map_repository():\n    return True\n", encoding="utf-8")
            out = root / "scan.json"
            completed = subprocess.run(
                [sys.executable, str(self.tool), "scan", "--path", str(artifact), "--out", str(out)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(out.exists())
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["decision"], "TOOL_CANDIDATE")
            self.assertIn("repository_mapping", payload["capabilities"])

if __name__ == "__main__":
    unittest.main()
