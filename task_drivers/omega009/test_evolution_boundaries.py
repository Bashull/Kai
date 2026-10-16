"""Own generator refusal cases; no provider execution or active installation."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('evolve009', Path(__file__).with_name('evolve_kpis009.py'))
EVOLVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVOLVE)
BASE = Path(os.environ['FORGE_BASE_BUNDLE']).resolve()
PIN = os.environ['FORGE_BASE_SHA256']


class KPIEvolutionBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='kai-evolution009-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_wrong_pin_creates_no_output(self):
        target = self.root / 'candidate'
        with self.assertRaisesRegex(ValueError, 'SHA'):
            EVOLVE.evolve(BASE, '0' * 64, target)
        self.assertFalse(target.exists())

    def test_stop_prevents_creation(self):
        stop = self.root / 'STOP'
        stop.touch()
        target = self.root / 'candidate'
        with self.assertRaises(RuntimeError):
            EVOLVE.evolve(BASE, PIN, target, stop)
        self.assertFalse(target.exists())

    def test_existing_user_directory_is_preserved(self):
        target = self.root / 'user-work'
        target.mkdir()
        witness = target / 'notes.txt'
        witness.write_bytes(b'preserve existing user work\n')
        with self.assertRaisesRegex(ValueError, 'new isolated'):
            EVOLVE.evolve(BASE, PIN, target)
        self.assertEqual(witness.read_bytes(), b'preserve existing user work\n')
        self.assertEqual(list(target.iterdir()), [witness])

    def test_active_installation_named_path_is_refused(self):
        target = self.root / '.codex' / 'skills' / 'candidate'
        with self.assertRaisesRegex(ValueError, 'Active installation'):
            EVOLVE.evolve(BASE, PIN, target)
        self.assertFalse((self.root / '.codex').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
