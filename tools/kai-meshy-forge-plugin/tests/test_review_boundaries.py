"""Independent boundary probes; every file/API is isolated or mocked."""
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import random
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from kai_meshy.core import Forge, ForgeError
from kai_meshy.core import digest
from kai_meshy.registry import AssetRegistry
from kai_meshy.recovery import snapshot, verify_restore
from kai_meshy import cli


class IndependentBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.forge = Forge(self.base / 'forge')
        self.registry = AssetRegistry(self.forge)

    def test_ancestor_symlink_cannot_register_private_file(self):
        private = self.base / 'private'; private.mkdir()
        (private / 'model.obj').write_text('v 0 0 0\n')
        link = self.forge.root / 'linked-directory'
        link.symlink_to(private, target_is_directory=True)
        with self.assertRaises(ForgeError):
            self.registry.register(link / 'model.obj', 'model')
        self.assertEqual(self.registry.list(), [])

    def test_secret_provenance_is_not_committed(self):
        asset = self.forge.root / 'asset.obj'; asset.write_text('v 0 0 0\n')
        with self.assertRaises(ForgeError):
            self.registry.register(asset, 'model', provenance={'author':'Bearer synthetic-fixture-secret'})
        self.assertEqual(self.registry.list(), [])

    def test_parent_integrity_is_required_before_derivation(self):
        parent = self.forge.root / 'parent.obj'; parent.write_text('v 0 0 0\n')
        record = self.registry.register(parent, 'model')
        parent.write_text('v 9 9 9\n')
        child = self.forge.root / 'child.obj'; child.write_text('v 1 1 1\n')
        with self.assertRaises(ForgeError):
            self.registry.register(child, 'derivative', parent_id=record['id'])
        with self.forge._db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM assets').fetchone()[0], 1)

    def test_backup_directory_symlink_cannot_copy_database_outside_scope(self):
        outside = self.base / 'outside'; outside.mkdir()
        (self.forge.root / 'backups').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ForgeError):
            snapshot(self.forge)
        self.assertEqual(list(outside.iterdir()), [])

    def test_restore_link_to_external_database_is_denied(self):
        outside = self.base / 'outside.sqlite3'
        with sqlite3.connect(outside) as db:
            db.execute('CREATE TABLE private_marker(value TEXT)')
        db.close()
        folder = self.forge.root / 'backups'; folder.mkdir()
        linked = folder / 'linked.sqlite3'; linked.symlink_to(outside)
        with self.assertRaises(ForgeError):
            verify_restore(self.forge, linked)

    def test_restore_preserves_backup_receipt_and_live_registry(self):
        asset = self.forge.root / 'evidence.txt'; asset.write_text('isolated recovery fixture')
        record = self.registry.register(asset, 'evidence')
        live_inode = self.forge.db.stat().st_ino
        receipt = snapshot(self.forge)
        restored = verify_restore(self.forge, receipt['path'])
        self.assertEqual(restored['backup_sha256'], receipt['sha256'])
        self.assertEqual(digest(receipt['path']), receipt['sha256'])
        self.assertEqual(self.forge.db.stat().st_ino, live_inode)
        self.assertEqual(self.registry.get(record['id'])['sha256'], record['sha256'])
        self.assertFalse(restored['live_database_replaced'])
        self.assertEqual(restored['scope'], 'SQLITE_STATE_ONLY_ASSET_RESTORE_SEPARATE')

    def test_expired_remote_metadata_does_not_block_verified_cache(self):
        from PIL import Image
        source = self.forge.root / 'reference.png'
        Image.frombytes('RGB', (64,64), random.Random(0).randbytes(64*64*3)).save(source)
        self.forge.create_job('EXPIRED', source, budget=36)
        preview = self.forge.root / 'jobs/EXPIRED/preview.png'
        preview.write_bytes(source.read_bytes())
        task_id = '00000000-0000-0000-0000-000000000001'
        with self.forge._db() as db:
            db.execute('INSERT INTO stages(job_id,stage,status,task_id,reservation,actual,intent_at,updated) VALUES(?,?,?,?,?,?,?,?)',
                       ('EXPIRED','prototype','SUCCEEDED',task_id,6,6,0,0))
            db.execute('INSERT INTO download_receipts VALUES(?,?,?,?,?,?,?,?)',
                       ('EXPIRED','prototype','preview',task_id,str(preview),digest(preview),preview.stat().st_size,0))
        self.forge.cli.api = MagicMock(side_effect=ForgeError('REMOTE_TASK_EXPIRED'))
        cached = self.forge.download('EXPIRED','prototype','preview')
        self.assertTrue(cached['cached'])
        self.assertEqual(cached['sha256'], digest(preview))
        self.forge.cli.api.assert_not_called()

    def test_refresh_cli_must_not_mutate_with_writes_disabled(self):
        fake = MagicMock()
        fake.refresh.return_value = {'status':'SUCCEEDED'}
        with patch.object(cli, 'make_forge', return_value=fake), \
             patch.dict(os.environ, {'KAI_MESHY_ALLOW_WRITES':'0'}, clear=False), \
             patch('sys.argv', ['kai-meshy-job-engine','refresh','AHU','prototype']), \
             redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                cli.main()
        fake.refresh.assert_not_called()

    def test_approval_cli_requires_both_write_and_approval_scopes(self):
        fake = MagicMock()
        fake.approve.return_value = {'preview_approved':True}
        with patch.object(cli, 'make_forge', return_value=fake), \
             patch.dict(os.environ, {'KAI_MESHY_ALLOW_WRITES':'0','KAI_MESHY_ALLOW_APPROVALS':'1'}, clear=False), \
             patch('sys.argv', ['kai-meshy-job-engine','approve','AHU','0'*64,'--actor','fixture-owner']), \
             redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                cli.main()
        fake.approve.assert_not_called()


if __name__ == '__main__':
    unittest.main()
