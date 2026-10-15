import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import kai_skill_auditor as auditor


def row(index=1, uri='skills://plugins/demo/one', content='---\nname: one\ndescription: Use for a synthetic test.\n---\nA\n'):
    return {'index': index, 'uri': uri, 'resources': [{'uri': uri, 'content': content}]}


class IntegrityRegressionTests(unittest.TestCase):
    def run_case(self, rows, expected=1):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            inp = base / 'input'
            inp.mkdir()
            (inp / 'skills_1.json').write_text(json.dumps(rows))
            with contextlib.redirect_stdout(io.StringIO()):
                rc = auditor.main(['--source', str(inp), '--out', str(base / 'out'), '--expected', str(expected)])
            exists = (base / 'out').exists()
            manifest = None
            if rc == 0:
                with zipfile.ZipFile(base / 'out/KAI_SKILLS_847_PRIVATE_CANDIDATE.zip') as z:
                    manifest = json.loads(z.read('MANIFEST.json'))
            return rc, exists, manifest

    def assert_blocked(self, rows, expected=1):
        rc, exists, _ = self.run_case(rows, expected)
        self.assertEqual(rc, 2)
        self.assertFalse(exists, 'Unresolved input must not generate a candidate release')

    def test_empty_body_cannot_be_success(self):
        self.assert_blocked([row(content='')])

    def test_conflicting_versions_cannot_be_success(self):
        self.assert_blocked([row(), row(content='Different revision')])

    def test_out_of_range_row_is_not_silently_dropped(self):
        self.assert_blocked([row(), row(index=2000)])

    def test_duplicate_identity_across_indices(self):
        self.assert_blocked([row(), row(index=2)], expected=2)

    def test_root_must_match_exact_resource_uri(self):
        r = row()
        r['resources'][0]['uri'] += '/references/unrelated.md'
        self.assert_blocked([r])

    def test_nul_is_not_silently_removed(self):
        self.assert_blocked([row(content='original\x00bytes')])

    def test_bool_is_not_an_index(self):
        self.assert_blocked([row(index=True)])

    def test_non_mapping_resources_are_reported(self):
        r = row()
        r['resources'] = ['bad']
        self.assert_blocked([r])

    def test_missing_indices_block_release(self):
        self.assert_blocked([row()], expected=2)

    def test_identical_duplicates_are_allowed(self):
        rc, exists, manifest = self.run_case([row(), row()])
        self.assertEqual(rc, 0)
        self.assertTrue(exists)
        self.assertEqual(manifest['total_expected'], 1)

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            (base / 'input').mkdir()
            (base / 'out').mkdir()
            sentinel = base / 'out/keep.txt'
            sentinel.write_text('preserve me')
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                auditor.main(['--source', str(base / 'input'), '--out', str(base / 'out')])
            self.assertEqual(sentinel.read_text(), 'preserve me')


if __name__ == '__main__':
    unittest.main()
