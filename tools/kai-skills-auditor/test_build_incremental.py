"""Synthetic incremental packaging tests; no provider or external service runs."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

import build_incremental as inc
import bundle_io as b


class IncrementalBuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='kai-incremental-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.base = self.root / 'base.zip'
        self.candidates = self.root / 'candidates'
        self.evidence = self.root / 'evidence'
        self.tools = self.root / 'current-tools'
        self.output = self.root / 'release'
        for directory in (self.candidates, self.evidence, self.tools):
            directory.mkdir()
        (self.evidence / 'BATCH_RESULT.json').write_text(json.dumps({
            'manual_ids': [2], 'functional_validation': 'NOT_RUN', 'scope': 'TEST_FIXTURE'}))
        (self.tools / 'bundle_io.py').write_text('# current own toolkit fixture\n')
        (self.tools / 'README.md').write_text('Current toolkit documentation\n')
        (self.tools / 'test_results.txt').write_text('OLD receipt must not become current\n')
        self.rows = []
        self.payload = {'reports/RESULT.json': b'{"old_tests":22}',
                        'reports/WEB_SOURCES.md': b'inherited web source scope',
                        'tools/bundle_io.py': b'old tool',
                        'tools/test_results.txt': b'inherited test receipt',
                        'README.md': b'old readme', 'catalog/847_ESTADO.csv': b'old csv',
                        'catalog/847_UNA_A_UNA.md': b'old numbered index'}
        for number, name in ((1, 'unchanged'), (2, 'changed')):
            original = f'originals/p/{name}/SKILL.md'
            staged = f'providers/p/skills/{name}'
            content = self.skill(name, 'base')
            self.payload[original] = content
            self.payload[staged + '/SKILL.md'] = content
            self.rows.append({'id': number, 'namespace': 'p', 'name': name,
                              'uri': f'skills://plugins/p/{name}', 'staged_root': staged,
                              'original_path': original, 'original_sha256': b.sha(content),
                              'portable_sha256': b.sha(content), 'candidate_sha256': b.sha(content),
                              'aux_expected': 0, 'aux_recovered': 0, 'aux_missing': [],
                              'support_files': [], 'state': 'BASE_CANDIDATE',
                              'functional_tests': 'NOT_RUN'})
        self.payload['providers/p/skills/changed/reference/old.txt'] = b'base resource'
        self.rows[1].update(aux_expected=1, aux_recovered=1,
                            support_files=['skills://plugins/p/changed/reference/old.txt'])
        self.write_base()
        self.tree = self.candidates / 'providers/p/skills/changed'
        self.tree.mkdir(parents=True)
        (self.tree / 'SKILL.md').write_bytes(self.skill('changed', 'candidate'))
        (self.tree / 'LICENSE').write_text('fixture license\n')
        (self.tree / 'SPEC.md').write_text('fixture specification\n')

    @staticmethod
    def skill(name, body):
        return f'---\nname: {name}\ndescription: Synthetic packaging fixture.\n---\n\n{body}\n'.encode()

    def write_base(self, manifest_change=None):
        payload = dict(self.payload)
        payload[b.CATALOG_PATH] = inc.json_bytes(self.rows)
        manifest = {'format': 'kai.skills.bundle/1', 'skills': len(self.rows),
                    'aux_recovered': sum(r['aux_recovered'] for r in self.rows), 'aux_missing': 0,
                    'files': {name: inc.record(data) for name, data in payload.items()}}
        if manifest_change:
            manifest_change(manifest)
        with zipfile.ZipFile(self.base, 'w') as archive:
            for name, data in payload.items():
                archive.writestr(name, data)
            archive.writestr('MANIFEST_SHA256.json', inc.json_bytes(manifest))

    def build(self, **kwargs):
        options = {'tools_dir': self.tools, 'expected_skills': 2}
        options.update(kwargs)
        return inc.build_incremental(self.base, self.candidates, self.evidence, self.output, **options)

    def assert_no_release(self):
        for name in ('release', 'release.zip', 'release.zip.sha256', 'release.zip.build.json'):
            self.assertFalse((self.root / name).exists(), name)

    def test_build_preserves_originals_and_unselected_trees_and_records_real_counts(self):
        receipt = self.build(base_sha256=b.sha(self.base.read_bytes()))
        self.assertEqual(receipt['candidate_ids'], [2])
        self.assertEqual(receipt['archive_integrity'], 'PASS')
        self.assertEqual(receipt['catalog_selective_dry_run']['mode'], 'DRY_RUN')
        self.assertFalse(Path(receipt['catalog_selective_dry_run']['target']).exists())
        self.assertFalse(receipt['provider_execution'])
        self.assertEqual(receipt['tests_run'], 'NOT_RUN_BY_BUILDER')
        for name, data in self.payload.items():
            if name.startswith(('originals/', 'providers/p/skills/unchanged/')):
                self.assertEqual((self.output / name).read_bytes(), data)
        catalog = json.loads((self.output / b.CATALOG_PATH).read_text())
        self.assertEqual(catalog[0], self.rows[0])
        changed = catalog[1]
        self.assertEqual(changed['original_sha256'], self.rows[1]['original_sha256'])
        self.assertEqual(changed['original_aux_expected'], 1)
        self.assertEqual(changed['captured_aux_expected'], 1)
        self.assertEqual(changed['aux_expected'], 2)  # LICENSE and SPEC are real packaged files.
        self.assertEqual(changed['aux_recovered'], 2)
        self.assertEqual(changed['support_files'], self.rows[1]['support_files'])
        self.assertEqual({r['path'] for r in changed['candidate_resource_files']}, {'LICENSE', 'SPEC.md'})
        candidate_hash = b.sha((self.tree / 'SKILL.md').read_bytes())
        self.assertEqual(changed['portable_sha256'], candidate_hash)
        self.assertEqual(changed['candidate_sha256'], candidate_hash)
        self.assertFalse((self.output / 'providers/p/skills/changed/reference/old.txt').exists())
        self.assertEqual((self.output / (inc.HISTORY + 'providers/p/skills/changed/reference/old.txt')).read_bytes(),
                         b'base resource')
        result = json.loads((self.output / 'reports/RESULT.json').read_text())
        self.assertEqual(result['observed_catalog_entries'], 2)
        self.assertEqual(result['trees_with_file_changes'], [2])
        self.assertEqual(result['state'], 'CANDIDATE_PARTIAL')
        archive = self.root / 'release.zip'
        self.assertEqual(b.sha(archive.read_bytes()), receipt['sha256'])
        self.assertEqual((self.root / 'release.zip.sha256').read_text().split()[0], receipt['sha256'])
        self.assertEqual(b.verify_bundle(archive)['aux_recovered'], 2)

    def test_historical_reports_tools_and_new_evidence_retain_separate_scopes(self):
        self.build()
        self.assertEqual((self.output / 'reports/INHERITED_V041_RESULT.json').read_bytes(),
                         self.payload['reports/RESULT.json'])
        self.assertEqual((self.output / 'reports/HISTORICAL/inherited_v041/WEB_SOURCES.md').read_bytes(),
                         self.payload['reports/WEB_SOURCES.md'])
        self.assertEqual((self.output / (inc.HISTORY + 'tools/test_results.txt')).read_bytes(),
                         self.payload['tools/test_results.txt'])
        self.assertEqual((self.output / 'tools/bundle_io.py').read_bytes(),
                         (self.tools / 'bundle_io.py').read_bytes())
        self.assertFalse((self.output / 'tools/test_results.txt').exists())
        self.assertEqual((self.output / 'batch_001/evidence/BATCH_RESULT.json').read_bytes(),
                         (self.evidence / 'BATCH_RESULT.json').read_bytes())
        with zipfile.ZipFile(self.base) as base:
            self.assertEqual((self.output / (inc.HISTORY + 'MANIFEST_SHA256.json')).read_bytes(),
                             base.read('MANIFEST_SHA256.json'))
        provenance = json.loads((self.output / 'batch_001/PROVENANCE.json').read_text())
        self.assertEqual(provenance['base_sha256_pin'], 'COMPUTED_NOT_EXTERNALLY_PINNED')

    def test_sha_pin_and_manifest_tampering_fail_before_output(self):
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            self.build(base_sha256='0' * 64)
        self.assert_no_release()
        self.write_base(lambda m: m['files']['README.md'].update(sha256='0' * 64))
        with self.assertRaisesRegex(ValueError, 'Manifest mismatch'):
            self.build()
        self.assert_no_release()

    def test_invalid_catalog_or_missing_original_fails_before_output(self):
        for change in ({'portable_sha256': '0' * 64}, {'id': 1},
                       {'staged_root': 'providers/other/skills/changed'}):
            with self.subTest(change=change):
                old = dict(self.rows[1])
                self.rows[1].update(change)
                self.write_base()
                with self.assertRaises(ValueError):
                    self.build()
                self.assert_no_release()
                self.rows[1] = old
        self.rows[1].pop('original_path')
        self.rows[1].pop('original_sha256')
        self.write_base()
        with self.assertRaisesRegex(ValueError, 'preserved original'):
            self.build()
        self.assert_no_release()

    def test_unknown_candidate_and_missing_skill_fail_before_output(self):
        rogue = self.candidates / 'providers/p/skills/unknown'
        rogue.mkdir()
        (rogue / 'SKILL.md').write_bytes(self.skill('unknown', 'unregistered'))
        with self.assertRaisesRegex(ValueError, 'Unknown candidate'):
            self.build()
        self.assert_no_release()
        (rogue / 'SKILL.md').unlink()
        rogue.rmdir()
        (self.tree / 'SKILL.md').unlink()
        with self.assertRaisesRegex(ValueError, 'contain SKILL.md'):
            self.build()
        self.assert_no_release()

    def test_candidate_frontmatter_identity_mismatch_rejected(self):
        (self.tree / 'SKILL.md').write_bytes(self.skill('different', 'wrong identity'))
        with self.assertRaisesRegex(ValueError, 'frontmatter name/description'):
            self.build()
        self.assert_no_release()

    def test_candidate_symlink_and_nonportable_path_rejected(self):
        link = self.tree / 'external.txt'
        try:
            link.symlink_to(self.base)
        except (OSError, NotImplementedError):
            self.skipTest('symlink creation unavailable')
        with self.assertRaisesRegex(ValueError, 'regular input'):
            self.build()
        self.assert_no_release()
        link.unlink()
        (self.tree / 'CON').write_text('unsafe Windows path')
        with self.assertRaisesRegex(ValueError, 'Nonportable'):
            self.build()
        self.assert_no_release()

    def test_recognizable_secret_in_new_evidence_blocks_without_printing_value(self):
        secret = 'ghp_' + 'A' * 40
        (self.evidence / 'accidental.txt').write_text(secret)
        with self.assertRaises(ValueError) as caught:
            self.build()
        self.assertNotIn(secret, str(caught.exception))
        self.assertIn('value withheld', str(caught.exception))
        self.assert_no_release()

    def test_existing_output_or_sibling_is_never_overwritten(self):
        for filename in ('release', 'release.zip', 'release.zip.sha256', 'release.zip.build.json',
                         'release_selective_dry_run'):
            with self.subTest(filename=filename):
                existing = self.root / filename
                existing.write_text('keep')
                with self.assertRaisesRegex(ValueError, 'must be new'):
                    self.build()
                self.assertEqual(existing.read_text(), 'keep')
                existing.unlink()

    def test_stop_before_build_and_during_copy_removes_only_owned_files(self):
        stop = self.root / 'STOP'
        stop.touch()
        with self.assertRaises(RuntimeError):
            self.build(stop_file=stop)
        self.assert_no_release()
        stop.unlink()
        original_write = b._write_new_file

        def stop_after_first_write(*args, **kwargs):
            original_write(*args, **kwargs)
            stop.touch()

        with mock.patch.object(b, '_write_new_file', side_effect=stop_after_first_write):
            with self.assertRaises(RuntimeError):
                self.build(stop_file=stop)
        self.assert_no_release()
        self.assertTrue(stop.exists())

    def test_failure_rollback_preserves_foreign_content(self):
        original_write = b._write_new_file

        def inject_then_fail(*args, **kwargs):
            original_write(*args, **kwargs)
            (self.output / 'foreign.txt').write_text('preserve')
            raise OSError('synthetic disk failure')

        with mock.patch.object(b, '_write_new_file', side_effect=inject_then_fail):
            with self.assertRaisesRegex(RuntimeError, 'cleanup incomplete'):
                self.build()
        self.assertEqual((self.output / 'foreign.txt').read_text(), 'preserve')
        self.assertEqual(list(self.output.iterdir()), [self.output / 'foreign.txt'])

    def test_expected_baseline_scope_is_an_assertion_not_a_claim(self):
        with self.assertRaisesRegex(ValueError, 'expected original ID scope'):
            self.build(expected_skills=847)
        self.assert_no_release()


if __name__ == '__main__':
    unittest.main()
