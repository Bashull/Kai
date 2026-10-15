"""Scoped support-pack regression tests using synthetic, executable-free fixtures."""
import json
from pathlib import Path
import unittest

import bundle_io as b
import build_incremental as inc
import test_build_incremental as fixtures


class ProviderResourceTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.IncrementalBuildTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.resources = self.f.root / 'resources'
        shared = self.resources / 'providers/p/shared'
        shared.mkdir(parents=True)
        (shared / 'contract.md').write_text('Shared fixture contract\n')
        self.path = 'providers/p/shared/contract.md'
        self.bindings = self.f.root / 'bindings.json'
        self.write_bindings([{'id': 2, 'files': [self.path]}])
        (self.f.tree / 'SKILL.md').write_bytes(self.f.skill('changed', '[contract](../../shared/contract.md)'))

    def write_bindings(self, bindings):
        self.bindings.write_text(json.dumps({'format': 'kai.skills.provider-bindings/1', 'bindings': bindings}))

    def build(self, **kwargs):
        return self.f.build(provider_resources=self.resources, resource_bindings=self.bindings, **kwargs)

    def test_selective_copy_keeps_relative_links_and_preserves_original_and_unselected_tree(self):
        receipt = self.build()
        self.assertEqual(receipt['resource_bound_ids'], [2])
        self.assertEqual(receipt['provider_resource_files'], 1)
        archive, target = self.f.root / 'release.zip', self.f.root / 'stage'
        stage = b.stage_selected(archive, [2], target, apply=True)
        self.assertEqual(stage['layout'], 'PROVIDER_SCOPED')
        skill = target / 'providers/p/skills/changed/SKILL.md'
        self.assertEqual((skill.parent / '../../shared/contract.md').resolve().read_text(), 'Shared fixture contract\n')
        self.assertFalse((target / 'providers/p/skills/unchanged').exists())
        self.assertFalse((target / 'originals').exists())
        self.assertEqual((self.f.output / 'originals/p/changed/SKILL.md').read_bytes(),
                         self.f.payload['originals/p/changed/SKILL.md'])
        self.assertEqual((self.f.output / 'providers/p/skills/unchanged/SKILL.md').read_bytes(),
                         self.f.payload['providers/p/skills/unchanged/SKILL.md'])
        self.assertEqual(b.rollback_stage(target)['mode'], 'ROLLBACK_DRY_RUN')
        self.assertTrue(skill.exists())
        b.rollback_stage(target, apply=True)
        self.assertFalse(target.exists())

    def test_shared_files_deduplicate_across_selected_ids_without_promoting_reviews(self):
        self.write_bindings([{'id': 1, 'files': [self.path]}, {'id': 2, 'files': [self.path]}])
        self.build()
        target = self.f.root / 'both'
        stage = b.stage_selected(self.f.root / 'release.zip', [1, 2], target, apply=True)
        self.assertEqual(stage['files'], 5)  # Two mains, two selected-tree resources, one shared file.
        rows = json.loads((self.f.output / b.CATALOG_PATH).read_text())
        self.assertNotIn('candidate_change_batches', rows[0])
        self.assertEqual(rows[0]['state'], self.f.rows[0]['state'])
        self.assertEqual(rows[0]['functional_tests'], 'NOT_RUN')
        b.rollback_stage(target, apply=True)

    def test_unknown_duplicate_and_empty_bindings_and_orphan_files_fail_before_output(self):
        invalid = [[], [{'id': 99, 'files': [self.path]}],
                   [{'id': 2, 'files': []}],
                   [{'id': 2, 'files': [self.path]}, {'id': 2, 'files': [self.path]}],
                   [{'id': 2, 'files': [self.path, self.path]}]]
        for bindings in invalid:
            with self.subTest(bindings=bindings):
                self.write_bindings(bindings)
                with self.assertRaises(ValueError):
                    self.build()
                self.f.assert_no_release()

    def test_cross_provider_other_skill_and_traversal_resources_cannot_enter_selection(self):
        for path in ['providers/other/shared/contract.md', 'providers/p/skills/unchanged/extra.md',
                     'providers/p/Skills/other/extra.md', 'providers/p/shared/SKILL.md',
                     'providers/p/shared/../secret.md', '../secret.md']:
            with self.subTest(path=path):
                self.write_bindings([{'id': 2, 'files': [path]}])
                with self.assertRaises(ValueError):
                    self.build()
                self.f.assert_no_release()

    def test_explicit_existing_sibling_auxiliary_is_copied_without_its_skill_entrypoint(self):
        auxiliary = 'providers/p/skills/unchanged/scripts/helper.mjs'
        self.f.payload[auxiliary] = b'export const fixture = 42;\n'
        self.f.rows[0].update(aux_expected=1, aux_recovered=1)
        self.f.write_base()
        self.write_bindings([{'id': 2, 'files': [self.path, auxiliary]}])
        self.build()
        target = self.f.root / 'with-sibling-auxiliary'
        b.stage_selected(self.f.root / 'release.zip', [2], target, apply=True)
        self.assertEqual((target / auxiliary).read_bytes(), self.f.payload[auxiliary])
        self.assertFalse((target / 'providers/p/skills/unchanged/SKILL.md').exists())
        self.assertEqual(json.loads((target / b.RECEIPT_NAME).read_text())['ids'], [2])
        b.rollback_stage(target, apply=True)
        self.assertFalse(target.exists())

    def test_skill_entrypoint_is_not_an_auxiliary_even_when_the_base_contains_it(self):
        for name in ['providers/p/skills/unchanged/SKILL.md', 'providers/p/skills/changed/SKILL.md']:
            with self.subTest(name=name):
                self.write_bindings([{'id': 2, 'files': [self.path, name]}])
                with self.assertRaisesRegex(ValueError, 'exclude skill entrypoints'):
                    self.build()
                self.f.assert_no_release()

    def test_subset_bundle_can_declare_auxiliary_source_without_selecting_its_owner(self):
        auxiliary = 'providers/p/skills/unchanged/scripts/helper.mjs'
        self.f.payload[auxiliary] = b'export const fixture = 42;\n'
        self.f.rows[0].update(aux_expected=1, aux_recovered=1)
        self.f.write_base()
        self.write_bindings([{'id': 2, 'files': [self.path, auxiliary]}])
        self.build()
        row = json.loads((self.f.output / b.CATALOG_PATH).read_text())[1]
        names = {row['original_path'], auxiliary, self.path}
        names.update(p.relative_to(self.f.output).as_posix()
                     for p in (self.f.output / row['staged_root']).rglob('*') if p.is_file())
        payload = {n: (self.f.output / n).read_bytes() for n in names}
        payload[b.CATALOG_PATH] = inc.json_bytes([row])
        manifest = inc._manifest(payload, [row])
        self.assertEqual(manifest['auxiliary_source_roots'], ['providers/p/skills/unchanged'])
        self.assertEqual(set(b._catalog_by_id(inc.PayloadReader(payload), manifest)), {2})
        manifest['auxiliary_source_roots'] = ['providers/other/skills/unchanged']
        with self.assertRaisesRegex(ValueError, 'auxiliary source root'):
            b._catalog_by_id(inc.PayloadReader(payload), manifest)

    def test_catalog_rejects_absent_resources_and_incorrect_hashes(self):
        for entry in [{'path': self.path, 'bytes': 2, 'sha256': '0' * 64},
                      {'path': 'providers/other/shared/x', 'bytes': 0, 'sha256': b.sha(b'')}]:
            with self.subTest(entry=entry):
                self.f.rows[1]['provider_resource_files'] = [entry]
                self.f.write_base()
                with self.assertRaises(ValueError):
                    self.build()
                self.f.assert_no_release()

    def test_replacing_shared_resource_preserves_old_bytes_and_rebinds_catalog(self):
        self.f.payload[self.path] = b'old shared bytes'
        self.f.rows[1]['provider_resource_files'] = [{'path': self.path, 'bytes': 16, 'sha256': b.sha(b'old shared bytes')}]
        self.f.write_base()
        self.build(batch_id='004')
        self.assertEqual((self.f.output / ('HISTORICAL/before_batch_004/' + self.path)).read_bytes(), b'old shared bytes')
        self.assertEqual((self.f.output / self.path).read_bytes(), (self.resources / self.path).read_bytes())

    def test_changed_resource_with_unrebound_consumer_is_rejected_before_output(self):
        self.f.payload[self.path] = b'old'
        self.f.rows[0]['provider_resource_files'] = [{'path': self.path, 'bytes': 3, 'sha256': b.sha(b'old')}]
        self.f.write_base()
        with self.assertRaisesRegex(ValueError, 'disagrees with the manifest'):
            self.build()
        self.f.assert_no_release()

    def test_foreign_or_changed_stage_files_block_provider_rollback(self):
        self.build()
        target = self.f.root / 'guarded'
        b.stage_selected(self.f.root / 'release.zip', [2], target, apply=True)
        witness = target / 'foreign.txt'
        witness.write_text('keep')
        with self.assertRaises(ValueError):
            b.rollback_stage(target, apply=True)
        self.assertEqual(witness.read_text(), 'keep')
        witness.unlink()
        shared = target / self.path
        shared.write_text('user edit')
        with self.assertRaisesRegex(ValueError, 'Manifest mismatch'):
            b.rollback_stage(target, apply=True)
        self.assertEqual(shared.read_text(), 'user edit')

    def test_stop_blocks_copy_and_rollback_before_mutation(self):
        self.build()
        archive, target, stop = self.f.root / 'release.zip', self.f.root / 'stopped', self.f.root / 'STOP'
        stop.write_text('')
        with self.assertRaises(RuntimeError):
            b.stage_selected(archive, [2], target, apply=True, stop_file=stop)
        self.assertFalse(target.exists())
        stop.unlink()
        b.stage_selected(archive, [2], target, apply=True)
        before = {p.relative_to(target).as_posix(): p.read_bytes() for p in target.rglob('*') if p.is_file()}
        stop.write_text('')
        with self.assertRaises(RuntimeError):
            b.rollback_stage(target, apply=True, stop_file=stop)
        after = {p.relative_to(target).as_posix(): p.read_bytes() for p in target.rglob('*') if p.is_file()}
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
