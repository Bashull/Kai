"""Regression: Loop Factory imports without optional parent dependencies."""
import os
from pathlib import Path
import subprocess
import sys
import unittest


class ImportIsolationTests(unittest.TestCase):
    def test_loop_factory_import_with_site_packages_disabled(self):
        repo = Path(__file__).resolve().parents[2]
        script = (
            "import core.loop_factory; "
            "from core.loop_factory import runner, store; "
            "assert 'requests' not in __import__('sys').modules; "
            "print('IMPORT_ISOLATED')"
        )
        result = subprocess.run(
            [sys.executable, "-S", "-c", script],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=15,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("IMPORT_ISOLATED", result.stdout)

    def test_unknown_public_symbol_fails_closed(self):
        import core
        with self.assertRaises(AttributeError):
            _ = core.nonexistent_facility


if __name__ == "__main__":
    unittest.main()
