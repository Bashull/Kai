"""Synthetic regression coverage for governed staging; no provider code runs."""
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock
import zipfile

import bundle_io as b


class StagingSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='kai-stage-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = self.root / 'bundle.zip'
        self.target = self.root / 'selected'

    def make(self, rows=None, payload=None, path=None, modes=None, manifest_edit=None):
        rows = rows if rows is not None else [{
            'id': 1, 'name': 'demo', 'namespace': 'p',
            'uri': 'skills://plugins/p/demo', 'staged_root': 'providers/p/skills/demo',
            'aux_missing': [], 'aux_expected': 1, 'aux_recovered': 1,
        }]
        payload = dict(payload) if payload is not None else {
            'providers/p/skills/demo/SKILL.md': b'verified skill',
            'providers/p/skills/demo/references/resource.txt': b'resource',
        }
        for row in rows:
            skill_path = row.get('staged_root', '') + '/SKILL.md'
            if skill_path in payload:
                row.setdefault('portable_sha256', b.sha(payload[skill_path]))
        payload['catalog/INDEX_847_RECONCILED.json'] = json.dumps(rows).encode()
        manifest = {
            'format': 'kai.skills.bundle/1', 'skills': len(rows),
            'aux_recovered': sum(r.get('aux_recovered', 0) for r in rows), 'aux_missing': 0,
            'files': {name: {'bytes': len(data), 'sha256': b.sha(data)}
                      for name, data in payload.items()},
        }
        if manifest_edit:
            manifest_edit(manifest)
        with zipfile.ZipFile(path or self.bundle, 'w') as z:
            for name, data in payload.items():
                if modes and name in modes:
                    info = zipfile.ZipInfo(name)
                    info.create_system = 3
                    info.external_attr = modes[name] << 16
                    z.writestr(info, data)
                else:
                    z.writestr(name, data)
            z.writestr('MANIFEST_SHA256.json', json.dumps(manifest))
        return rows, payload

    def assert_rejected_before_write(self, ids=(1,)):
        with self.assertRaises(ValueError):
            b.stage_selected(self.bundle, ids, self.target, apply=False)
        self.assertFalse(self.target.exists())
        with self.assertRaises(ValueError):
            b.stage_selected(self.bundle, ids, self.target, apply=True)
        self.assertFalse(self.target.exists())

    def test_good_dryrun_and_apply_preserve_bytes_and_record_receipt(self):
        _, payload = self.make()
        dry = b.stage_selected(self.bundle, [1, 1], self.target)
        self.assertEqual(dry['files'], 2)
        self.assertFalse(self.target.exists())
        staged = b.stage_selected(self.bundle, [1], self.target, apply=True)
        receipt = json.loads(Path(staged['receipt']).read_text())
        self.assertEqual(receipt['ids'], [1])
        self.assertFalse(receipt['executed_bundled_code'])
        self.assertEqual(len(receipt['files']), 2)
        for item in receipt['files']:
            data = (self.target / item['path']).read_bytes()
            self.assertEqual(data, payload[item['source']])
            self.assertEqual(b.sha(data), item['sha256'])

    def test_duplicate_ids_rejected_instead_of_last_wins(self):
        rows, payload = self.make()
        rows += [dict(rows[0])]
        self.make(rows=rows, payload=payload)
        self.assert_rejected_before_write()

    def test_malformed_catalog_fields_rejected_before_write(self):
        rows, payload = self.make()
        changes = [
            {'id': True}, {'id': 0}, {'name': '../escape'}, {'name': 'Demo'},
            {'namespace': '../outside'}, {'staged_root': 'providers/other/skills/demo'},
            {'uri': 'skills://plugins/unrelated/demo'}, {'portable_sha256': '0'*64},
            {'aux_missing': 'not-a-list'}, {'aux_recovered': 17}, {'aux_expected': True},
        ]
        for change in changes:
            with self.subTest(change=change):
                self.make(rows=[dict(rows[0], **change)], payload=payload)
                self.assert_rejected_before_write()

    def test_missing_skill_root_cannot_succeed_with_zero_files(self):
        rows, _ = self.make()
        self.make(rows=rows, payload={'unrelated.txt': b'data'})
        self.assert_rejected_before_write()

    def test_manifest_catalog_counts_must_agree(self):
        for change in ({'skills': 2}, {'skills': True}, {'aux_recovered': 0}, {'aux_missing': 1}):
            with self.subTest(change=change):
                self.make(manifest_edit=lambda m: m.update(change))
                self.assert_rejected_before_write()

    def test_skill_original_hash_if_present_must_match(self):
        rows, payload = self.make()
        rows[0].update(original_path='originals/p/demo/SKILL.md', original_sha256='0'*64)
        payload['originals/p/demo/SKILL.md'] = b'original'
        self.make(rows=rows, payload=payload)
        self.assert_rejected_before_write()

    def test_missing_resources_remain_blocked(self):
        rows, payload = self.make()
        rows[0].update(aux_missing=['missing-reference'], aux_expected=2)
        self.make(rows=rows, payload=payload)
        self.assert_rejected_before_write()

    def test_selected_ids_cannot_be_boolean_or_empty(self):
        self.make()
        self.assert_rejected_before_write(ids=(True,))
        self.assert_rejected_before_write(ids=())

    def test_same_name_different_providers_is_blocked(self):
        rows, payload = self.make()
        other = dict(rows[0], id=2, namespace='q', uri='skills://plugins/q/demo',
                     staged_root='providers/q/skills/demo', aux_expected=0, aux_recovered=0)
        payload['providers/q/skills/demo/SKILL.md'] = b'verified skill'
        self.make(rows=rows+[other], payload=payload)
        self.assert_rejected_before_write(ids=(1, 2))

    def test_file_directory_prefix_collisions_rejected_before_write(self):
        for prefix in ('providers/p/skills/demo/references', 'providers/p/skills/demo/REFERENCES'):
            with self.subTest(prefix=prefix):
                rows, payload = self.make()
                payload[prefix] = b'cannot also be a directory'
                rows[0].update(aux_expected=2, aux_recovered=2)
                self.make(rows=rows, payload=payload)
                self.assert_rejected_before_write()

    def test_windows_unsafe_paths_are_rejected(self):
        for name in ('CON', 'nul.txt', 'demo/a.', 'demo/a ', 'dir/a?b', 'dir/a|b'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                b.safe_path(name)

    def test_unicode_normalization_case_collisions_are_rejected(self):
        rows, payload = self.make()
        payload['extra/caf\u00e9.txt'] = b'a'
        payload['extra/cafe\u0301.txt'] = b'b'
        self.make(rows=rows, payload=payload)
        with self.assertRaises(ValueError):
            b.verify_bundle(self.bundle)

    def test_nonregular_modes_are_rejected(self):
        for kind in (stat.S_IFIFO, stat.S_IFSOCK, stat.S_IFBLK, stat.S_IFCHR):
            with self.subTest(kind=kind):
                rows, payload = self.make()
                self.make(rows=rows, payload=payload,
                          modes={'providers/p/skills/demo/SKILL.md': kind | 0o600})
                with self.assertRaises(ValueError):
                    b.verify_bundle(self.bundle)

    def test_manifest_boolean_size_is_not_an_integer_size(self):
        self.make(payload={'x': b'a'}, manifest_edit=lambda m: m['files']['x'].update(bytes=True))
        with self.assertRaises(ValueError):
            b.verify_bundle(self.bundle)

    def test_archive_path_is_opened_once_and_replacement_cannot_supply_bytes(self):
        self.make()
        replacement = self.root / 'replacement.zip'
        self.make(path=replacement, payload={
            'providers/p/skills/demo/SKILL.md': b'unverified replacement',
            'providers/p/skills/demo/references/resource.txt': b'resource',
        })
        real_zip = zipfile.ZipFile
        opens = []

        def open_zip(path, *args, **kwargs):
            opens.append(str(path))
            if len(opens) == 2:
                os.replace(replacement, self.bundle)
            return real_zip(path, *args, **kwargs)

        with mock.patch.object(b.zipfile, 'ZipFile', side_effect=open_zip):
            b.stage_selected(self.bundle, [1], self.target, apply=True)
        self.assertEqual(len(opens), 1)
        self.assertEqual((self.target/'demo/SKILL.md').read_bytes(), b'verified skill')

    def test_write_failure_rolls_back_only_new_stage(self):
        self.make()
        sentinel = self.root/'outside.txt'
        sentinel.write_text('keep')
        real_open = Path.open

        def failing_open(path, mode='r', *args, **kwargs):
            if mode == 'xb' and path.name == 'resource.txt':
                raise OSError('synthetic full disk')
            return real_open(path, mode, *args, **kwargs)

        with mock.patch.object(Path, 'open', failing_open), self.assertRaises(OSError):
            b.stage_selected(self.bundle, [1], self.target, apply=True)
        self.assertFalse(self.target.exists())
        self.assertEqual(sentinel.read_text(), 'keep')

    def test_bytes_are_rechecked_after_validation_before_each_write(self):
        self.make()
        real_catalog = b._catalog_by_id

        def corrupt_subsequent_read(z, manifest):
            result = real_catalog(z, manifest)
            read = z.read

            def changed(name, *args, **kwargs):
                if name == 'providers/p/skills/demo/SKILL.md':
                    return b'modified after verification'
                return read(name, *args, **kwargs)

            z.read = changed
            return result

        with mock.patch.object(b, '_catalog_by_id', side_effect=corrupt_subsequent_read):
            with self.assertRaisesRegex(ValueError, 'Manifest mismatch'):
                b.stage_selected(self.bundle, [1], self.target, apply=True)
        self.assertFalse(self.target.exists())

    def test_failure_cleanup_preserves_foreign_data_and_reports_incomplete(self):
        self.make()
        real_open = Path.open

        def inject_foreign_then_fail(path, mode='r', *args, **kwargs):
            if mode == 'xb' and path.name == 'resource.txt':
                (self.target/'foreign.txt').write_text('preserve external data')
                raise OSError('synthetic write failure')
            return real_open(path, mode, *args, **kwargs)

        with mock.patch.object(Path, 'open', inject_foreign_then_fail):
            with self.assertRaisesRegex(RuntimeError, 'cleanup incomplete'):
                b.stage_selected(self.bundle, [1], self.target, apply=True)
        self.assertEqual((self.target/'foreign.txt').read_text(), 'preserve external data')
        self.assertFalse((self.target/'demo').exists())
        self.assertFalse((self.target/b.RECEIPT_NAME).exists())

    def test_existing_stage_is_never_overwritten_or_cleaned(self):
        self.make()
        self.target.mkdir()
        sentinel = self.target/'existing.txt'
        sentinel.write_text('keep')
        with self.assertRaises(ValueError):
            b.stage_selected(self.bundle, [1], self.target, apply=True)
        self.assertEqual(sentinel.read_text(), 'keep')

    def test_stop_before_stage_and_between_files_cleans_new_files(self):
        self.make()
        stop = self.root/'STOP'
        stop.touch()
        with self.assertRaises(RuntimeError):
            b.stage_selected(self.bundle, [1], self.target, apply=True, stop_file=stop)
        self.assertFalse(self.target.exists())
        stop.unlink()
        real_open = Path.open

        def request_stop_after_open(path, mode='r', *args, **kwargs):
            if mode == 'xb' and path.name == 'SKILL.md':
                stop.touch()
            return real_open(path, mode, *args, **kwargs)

        with mock.patch.object(Path, 'open', request_stop_after_open), self.assertRaises(RuntimeError):
            b.stage_selected(self.bundle, [1], self.target, apply=True, stop_file=stop)
        self.assertFalse(self.target.exists())
        self.assertTrue(stop.exists())

    def test_completed_stage_rollback_dryrun_preserves_everything(self):
        self.make()
        b.stage_selected(self.bundle, [1], self.target, apply=True)
        before = {str(p.relative_to(self.target)): p.read_bytes()
                  for p in self.target.rglob('*') if p.is_file()}
        result = b.rollback_stage(self.target)
        self.assertEqual(result['mode'], 'ROLLBACK_DRY_RUN')
        self.assertEqual(result['files'], 2)
        self.assertEqual(before, {str(p.relative_to(self.target)): p.read_bytes()
                                 for p in self.target.rglob('*') if p.is_file()})

    def test_completed_stage_rollback_removes_only_the_new_lab(self):
        self.make()
        sentinel = self.root/'outside.txt'
        sentinel.write_text('keep')
        b.stage_selected(self.bundle, [1], self.target, apply=True)
        result = b.rollback_stage(self.target, apply=True)
        self.assertEqual(result['mode'], 'ROLLED_BACK')
        self.assertFalse(self.target.exists())
        self.assertEqual(sentinel.read_text(), 'keep')

    def test_modified_extra_symlink_or_missing_payload_blocks_all_rollback(self):
        self.make()
        for case in ('modified', 'extra', 'symlink', 'missing'):
            with self.subTest(case=case):
                target = self.root/('stage-'+case)
                b.stage_selected(self.bundle, [1], target, apply=True)
                skill = target/'demo/SKILL.md'
                if case == 'modified':
                    skill.write_bytes(b'keep edited work')
                elif case == 'extra':
                    (target/'foreign.txt').write_text('keep foreign data')
                elif case == 'symlink':
                    skill.unlink()
                    skill.symlink_to(self.bundle)
                elif case == 'missing':
                    skill.unlink()
                before = {str(p.relative_to(target)): (p.is_symlink(), p.read_bytes() if p.is_file() and not p.is_symlink() else None)
                          for p in target.rglob('*')}
                for apply in (False, True):
                    with self.assertRaises(ValueError):
                        b.rollback_stage(target, apply=apply)
                after = {str(p.relative_to(target)): (p.is_symlink(), p.read_bytes() if p.is_file() and not p.is_symlink() else None)
                         for p in target.rglob('*')}
                self.assertEqual(before, after)

    def test_rollback_rejects_root_active_trees_symlink_targets_and_bad_receipts(self):
        self.make()
        b.stage_selected(self.bundle, [1], self.target, apply=True)
        alias = self.root/'alias'
        alias.symlink_to(self.target, target_is_directory=True)
        for target in (Path(self.target.anchor), self.root/'.agents'/'synthetic', alias):
            with self.subTest(target=target), self.assertRaises(ValueError):
                b.rollback_stage(target, apply=True)
        receipt = self.target/b.RECEIPT_NAME
        original = receipt.read_bytes()
        receipt.write_text('{"format":"unrelated","files":[]}')
        with self.assertRaises(ValueError):
            b.rollback_stage(self.target, apply=True)
        self.assertEqual((self.target/'demo/SKILL.md').read_bytes(), b'verified skill')
        receipt.write_bytes(original)
        stop = self.root/'STOP'
        stop.touch()
        with self.assertRaises(RuntimeError):
            b.rollback_stage(self.target, apply=True, stop_file=stop)
        self.assertTrue(self.target.exists())


if __name__ == '__main__':
    unittest.main()
