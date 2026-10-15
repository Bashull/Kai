import json
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

import bundle_io as b


class BundleTests(unittest.TestCase):
    def create(self, path, payload=None, extras=None):
        payload = payload or {'a.txt': b'preserved'}
        files = {name: {'bytes': len(data), 'sha256': b.sha(data)} for name, data in payload.items()}
        manifest = {'format': 'kai.skills.bundle/1', 'skills': 1, 'aux_recovered': 0,
                    'aux_missing': 0, 'files': files}
        with zipfile.ZipFile(path, 'w') as z:
            for name, data in payload.items():
                z.writestr(name, data)
            z.writestr('MANIFEST_SHA256.json', json.dumps(manifest))
            for name, data in (extras or {}).items():
                z.writestr(name, data)

    def test_manifest_covers_payload(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'good.zip'
            self.create(p)
            self.assertEqual(len(b.verify_bundle(p)['files']), 1)

    def test_unlisted_file_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'bad.zip'
            self.create(p, extras={'unlisted.txt': b'x'})
            with self.assertRaises(ValueError):
                b.verify_bundle(p)

    def test_modified_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'bad.zip'
            self.create(p)
            with zipfile.ZipFile(p) as z:
                m = z.read('MANIFEST_SHA256.json')
            with zipfile.ZipFile(p, 'w') as z:
                z.writestr('a.txt', b'modified')
                z.writestr('MANIFEST_SHA256.json', m)
            with self.assertRaises(ValueError):
                b.verify_bundle(p)

    def test_traversal_and_windows_paths_rejected(self):
        for name in ('../escape', '/absolute', 'C:/escape', 'dir\\escape', 'dir/../escape', 'dir//a'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                b.safe_path(name)

    def test_case_collisions_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'bad.zip'
            self.create(p, {'A.txt': b'a', 'a.txt': b'b'})
            with self.assertRaises(ValueError):
                b.verify_bundle(p)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'bad.zip'
            self.create(p)
            link = zipfile.ZipInfo('link')
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(p, 'a') as z:
                z.writestr(link, '../outside')
            with self.assertRaises(ValueError):
                b.verify_bundle(p)


if __name__ == '__main__':
    unittest.main()
