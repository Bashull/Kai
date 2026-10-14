"""Legacy core import contract for Loop Factory isolated import patch.

This test invokes only imports in child interpreters. It never runs
Fetcher, downloads data, or changes user project files.
"""
import os
from pathlib import Path
import subprocess
import sys
import unittest


class LegacyCoreApiTests(unittest.TestCase):
    def _isolated(self, script: str) -> str:
        repo = Path(__file__).resolve().parents[2]
        proc = subprocess.run(
            [sys.executable, "-S", "-c", script],
            cwd=repo,
            capture_output=True, text=True, timeout=20,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc.stdout

    def test_public_symbol_order_and_names_unchanged(self):
        stdout = self._isolated(
            "import core,sys\n"
            "assert core.__all__ == ['Fetcher', 'Adapter', 'RepositoryScanner', 'Synthesizer', 'Refactorer', 'LocalTrainer', 'SelfAuditor', 'FeedbackController', 'EvolutionEngine']\n"
            "assert 'requests' not in sys.modules\n"
            "print('LEGACY_NAMES_STABLE')\n"
        )
        self.assertIn("LEGACY_NAMES_STABLE",stdout)

    def test_eight_stdlib_legacy_exports_import_without_requests(self):
        stdout = self._isolated(
            "import core,sys\n"
            "from core import Adapter, RepositoryScanner, Synthesizer, Refactorer, LocalTrainer, SelfAuditor, FeedbackController, EvolutionEngine\n"
            "for name in core.__all__[1:]:\n"
            "    obj = getattr(core,name)\n"
            "    assert obj.__name__ == name and obj.__module__.startswith('core.')\n"
            "assert 'requests' not in sys.modules\n"
            "print('LEGACY_EIGHT_WORK')\n"
        )
        self.assertIn("LEGACY_EIGHT_WORK",stdout)

    def test_fetcher_explicit_import_reports_missing_optional_dependency(self):
        stdout = self._isolated(
            "try:\n"
            "    from core import Fetcher\n"
            "except ModuleNotFoundError as exc:\n"
            "    assert exc.name == 'requests', exc\n"
            "    print('OPTIONAL_DEPENDENCY_VISIBLE')\n"
            "else:\n"
            "    assert Fetcher.__name__ == 'Fetcher'\n"
            "    print('FETCHER_AVAILABLE')\n"
        )
        self.assertTrue("OPTIONAL_DEPENDENCY_VISIBLE" in stdout or "FETCHER_AVAILABLE" in stdout)


if __name__ == "__main__":
    unittest.main()
