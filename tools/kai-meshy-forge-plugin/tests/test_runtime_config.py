import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from kai_meshy.cli import make_forge
from kai_meshy.core import ForgeError


class RuntimeConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.config = self.home / '.config/kai-meshy-forge/runtime.json'
        self.config.parent.mkdir(parents=True)
        self.runtime = self.home / 'runtime'
        self.runtime.mkdir()
        self.value = {'schema': 'kai.meshy.runtime/v1', 'workspace': str(self.runtime), 'cli': '/installed/meshy', 'reference_roots': [str(self.runtime)]}

    def write(self):
        self.config.write_text(json.dumps(self.value))
        self.config.chmod(0o600)

    def test_pointer_config_does_not_grant_spending(self):
        self.write()
        with patch('pathlib.Path.home', return_value=self.home), patch.dict(os.environ, {}, clear=True):
            forge = make_forge()
        self.assertEqual(forge.root, self.runtime)
        self.assertEqual(forge.cli.executable, '/installed/meshy')
        self.assertFalse(forge.spending_enabled)
        self.assertFalse(forge.spending_job_ids)

    def test_public_config_or_permission_fields_denied(self):
        self.write(); self.config.chmod(0o644)
        with patch('pathlib.Path.home', return_value=self.home), patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ForgeError, 'PRIVATE'):
                make_forge()
        self.value['spending_enabled'] = True
        self.write()
        with patch('pathlib.Path.home', return_value=self.home), patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ForgeError, 'FIELDS'):
                make_forge()


if __name__ == '__main__':
    unittest.main()
