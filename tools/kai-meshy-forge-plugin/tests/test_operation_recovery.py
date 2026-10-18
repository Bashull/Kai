"""Backups must include each path occurrence, even when content deduplicates."""
import json
from pathlib import Path
import random
import tempfile
import unittest

from PIL import Image

from kai_meshy.capability_engine import CapabilityEngine
from kai_meshy.core import Forge, ForgeError
from kai_meshy.recovery import recovery_files, snapshot
from kai_meshy.registry import AssetRegistry


class OperationRecoveryTests(unittest.TestCase):
    def test_deduplicated_media_occurrence_is_recoverable_and_tamper_blocks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            forge = Forge(root)
            original = root / 'original.png'
            Image.frombytes('RGB', (32, 32), random.Random(37).randbytes(32*32*3)).save(original)
            registry = AssetRegistry(forge)
            registry.register(original, 'reference')
            engine = CapabilityEngine(forge)
            engine.create_operation('RECOVERY', 'image_to_3d.generate',
                                    {'image_url': {'local_path': str(original)}}, budget=36)
            row = engine._row('RECOVERY', 'main')
            manifest = json.loads(Path(row['manifest_path']).read_text())
            occurrence = Path(manifest['parameters']['image_url']['reference']['local_copy'])
            self.assertNotEqual(occurrence, original)
            backup = snapshot(forge)
            inventory = recovery_files(forge, backup['path'])
            paths = {x['path']: x for x in inventory['files']}
            self.assertIn(original.relative_to(root).as_posix(), paths)
            self.assertIn(occurrence.relative_to(root).as_posix(), paths)
            self.assertIn('operation_media_occurrence', paths[occurrence.relative_to(root).as_posix()]['purposes'])
            self.assertFalse(inventory['cli_credentials_included'])
            self.assertEqual(len(list(root.glob('backups/*.sqlite3'))), 1)
            occurrence.write_bytes(b'changed copy preserved for diagnosis')
            with self.assertRaisesRegex(ForgeError, 'RECOVERY_REFERENCED_FILE_CHANGED'):
                recovery_files(forge, backup['path'])
            self.assertTrue(original.is_file())

    def test_unregistered_download_occurrence_is_collected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            forge = Forge(root)
            original = root / 'original.png'
            Image.frombytes('RGB', (32, 32), random.Random(18).randbytes(32*32*3)).save(original)
            forge.create_job('job', original, budget=36)
            extra = root / 'download.bin'; extra.write_bytes(b'existing output bytes')
            from kai_meshy.core import digest
            with forge._db() as db:
                db.execute('INSERT INTO download_receipts(job_id,stage,format,task_id,path,sha256,bytes,created) VALUES(?,?,?,?,?,?,?,?)',
                           ('job', 'prototype', 'image:0', '00000000-0000-0000-0000-000000000001', str(extra), digest(extra), extra.stat().st_size, 1))
            inventory = recovery_files(forge, snapshot(forge)['path'])
            self.assertIn('download.bin', {r['path'] for r in inventory['files']})


if __name__ == '__main__':
    unittest.main()
