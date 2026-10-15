"""Four stdlib-only native staging checks; no provider code or external services."""
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import bundle_io as b


class NativeSupportStageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='kai-native-support-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.archive = self.root / 'fixture.zip'
        self.target = self.root / 'stage'
        self.skill = 'providers/p/skills/board/SKILL.md'
        self.contract = 'providers/p/shared/contract.md'
        self.auxiliary = 'providers/p/skills/source-helper/scripts/fixture.txt'
        self.payload = {self.skill: b'fixture skill; never executed',
                        self.contract: b'common fixture contract', self.auxiliary: b'auxiliary fixture'}
        row = {'id': 1, 'name': 'board', 'namespace': 'p', 'uri': 'skills://plugins/p/board',
               'staged_root': 'providers/p/skills/board', 'portable_sha256': b.sha(self.payload[self.skill]),
               'aux_missing': [], 'aux_expected': 0, 'aux_recovered': 0,
               'provider_resource_files': [{'path': n, 'bytes': len(self.payload[n]), 'sha256': b.sha(self.payload[n])}
                                           for n in [self.contract, self.auxiliary]]}
        self.payload[b.CATALOG_PATH] = json.dumps([row]).encode()
        manifest = {'format': 'kai.skills.bundle/1', 'skills': 1, 'aux_recovered': 0, 'aux_missing': 0,
                    'auxiliary_source_roots': ['providers/p/skills/source-helper'],
                    'files': {n: {'bytes': len(d), 'sha256': b.sha(d)} for n, d in self.payload.items()}}
        with zipfile.ZipFile(self.archive, 'x') as z:
            for n, d in self.payload.items(): z.writestr(n, d)
            z.writestr('MANIFEST_SHA256.json', json.dumps(manifest))

    def test_native_provider_layout_and_rollback_roundtrip(self):
        self.assertEqual(b.stage_selected(self.archive, [1], self.target)['files'], 3)
        self.assertFalse(self.target.exists())
        result = b.stage_selected(self.archive, [1], self.target, apply=True)
        self.assertEqual(result['layout'], 'PROVIDER_SCOPED')
        for n in [self.skill, self.contract, self.auxiliary]:
            self.assertEqual((self.target / n).read_bytes(), self.payload[n])
        self.assertFalse((self.target / 'providers/p/skills/source-helper/SKILL.md').exists())
        self.assertEqual(b.rollback_stage(self.target)['mode'], 'ROLLBACK_DRY_RUN')
        b.rollback_stage(self.target, apply=True)
        self.assertFalse(self.target.exists())

    def test_foreign_file_blocks_rollback_without_removing_it(self):
        b.stage_selected(self.archive, [1], self.target, apply=True)
        foreign = self.target / 'user.txt'; foreign.write_text('keep')
        with self.assertRaises(ValueError): b.rollback_stage(self.target, apply=True)
        self.assertEqual(foreign.read_text(), 'keep')
        self.assertTrue((self.target / self.skill).exists())

    def test_changed_resource_blocks_rollback_before_removing_the_skill(self):
        b.stage_selected(self.archive, [1], self.target, apply=True)
        (self.target / self.contract).write_text('user edit')
        with self.assertRaises(ValueError): b.rollback_stage(self.target, apply=True)
        self.assertTrue((self.target / self.skill).exists())

    def test_stop_blocks_staging_before_target_creation(self):
        stop = self.root / 'STOP'; stop.write_text('')
        with self.assertRaises(RuntimeError):
            b.stage_selected(self.archive, [1], self.target, apply=True, stop_file=stop)
        self.assertFalse(self.target.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
