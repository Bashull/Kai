"""Regression: consecutive incremental batches must preserve both ancestries."""
from pathlib import Path
import json
import unittest
import zipfile

import build_incremental as inc
import bundle_io as b
import test_build_incremental as fixtures


class IncrementalChainTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.IncrementalBuildTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_two_batches_preserve_first_evidence_and_both_previous_skill_versions(self):
        f = self.fixture
        first = f.build()
        first_path = Path(first['zip'])
        before = first_path.read_bytes()
        (f.tree / 'SKILL.md').write_bytes(f.skill('changed', 'second candidate'))
        second = inc.build_incremental(first_path, f.candidates, f.evidence, f.root/'second',
            base_sha256=b.sha(before), tools_dir=f.tools, expected_skills=2, batch_id='002')
        self.assertEqual(first_path.read_bytes(), before)
        with zipfile.ZipFile(first_path) as a, zipfile.ZipFile(second['zip']) as z:
            for name in a.namelist():
                if name.startswith(('originals/', 'batch_001/', inc.HISTORY)):
                    self.assertEqual(z.read(name), a.read(name), name)
            old = 'providers/p/skills/changed/SKILL.md'
            self.assertEqual(z.read('HISTORICAL/before_batch_002/' + old), a.read(old))
            self.assertEqual(z.read(old), (f.tree/'SKILL.md').read_bytes())
            self.assertEqual(json.loads(z.read('batch_002/PROVENANCE.json'))['base_zip_sha256'], b.sha(before))
            row = json.loads(z.read(b.CATALOG_PATH))[1]
            self.assertEqual(row['candidate_change_batches'], ['001', '002'])
        self.assertEqual(b.verify_bundle(second['zip'])['skills'], 2)

    def test_duplicate_batch_and_invalid_batch_ids_rejected_without_writes(self):
        f = self.fixture
        first = f.build()
        for i, batch in enumerate(('001', '000', '../x', '2', True, 2)):
            target = f.root / ('rejected-' + str(i))
            with self.subTest(batch=batch), self.assertRaises(ValueError):
                inc.build_incremental(Path(first['zip']), f.candidates, f.evidence, target,
                    tools_dir=f.tools, expected_skills=2, batch_id=batch)
            self.assertFalse(target.exists())
            self.assertFalse(target.with_suffix('.zip').exists())

    def test_legacy_unselected_row_recovers_lineage_from_immutable_changes(self):
        f = self.fixture
        first = f.build()
        with zipfile.ZipFile(first['zip']) as source:
            payload = {n: source.read(n) for n in source.namelist()
                       if n != 'MANIFEST_SHA256.json'}
        catalog = json.loads(payload[b.CATALOG_PATH])
        for row in catalog:
            row.pop('candidate_change_batches', None)  # Valid legacy catalog.
        payload[b.CATALOG_PATH] = inc.json_bytes(catalog)
        manifest = inc._manifest(payload, catalog)
        legacy = f.root/'legacy.zip'
        with zipfile.ZipFile(legacy, 'w') as z:
            for name, data in payload.items():
                z.writestr(name, data)
            z.writestr('MANIFEST_SHA256.json', inc.json_bytes(manifest))
        other = f.root/'other-candidates'
        tree = other/'providers/p/skills/unchanged'
        tree.mkdir(parents=True)
        (tree/'SKILL.md').write_bytes(f.skill('unchanged', 'new explicit selection'))
        second = inc.build_incremental(legacy, other, f.evidence, f.root/'second',
            tools_dir=f.tools, expected_skills=2, batch_id='002')
        with zipfile.ZipFile(second['zip']) as z:
            rows = json.loads(z.read(b.CATALOG_PATH))
            self.assertEqual(rows[0]['candidate_change_batches'], ['002'])
            self.assertEqual(rows[1]['candidate_change_batches'], ['001'])
            self.assertEqual(z.read('batch_001/CHANGES.json'), payload['batch_001/CHANGES.json'])
            name = 'providers/p/skills/changed/SKILL.md'
            self.assertEqual(z.read(name), payload[name])


if __name__ == '__main__':
    unittest.main()
