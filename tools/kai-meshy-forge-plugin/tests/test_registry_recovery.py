import tempfile
import unittest
from pathlib import Path
from PIL import Image
from kai_meshy.core import Forge, ForgeError
from kai_meshy.registry import AssetRegistry
from kai_meshy.recovery import snapshot, verify_restore


class RegistryRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'forge'
        self.forge = Forge(self.root)
        self.registry = AssetRegistry(self.forge)
        self.image = self.root / 'reference.png'
        Image.new('RGB', (64, 96), (128, 128, 128)).save(self.image)

    def test_lineage_parent_and_mutation(self):
        parent = self.registry.register(self.image, 'reference')
        child_file = self.root / 'derivative.png'
        Image.new('RGB', (64, 96), (130, 130, 130)).save(child_file)
        child = self.registry.register(child_file, 'derivative', parent['id'])
        self.assertEqual(child['parent_id'], parent['id'])
        self.image.write_bytes(b'changed')
        with self.assertRaisesRegex(ForgeError, 'IMMUTABLE_ASSET_CHANGED'):
            self.registry.get(parent['id'])

    def test_path_scope_and_invalid_parent(self):
        other = Path(self.temp.name) / 'private.png'
        Image.new('RGB', (64, 64)).save(other)
        with self.assertRaisesRegex(ForgeError, 'OUTSIDE_WORKSPACE'):
            self.registry.register(other, 'reference')
        with self.assertRaisesRegex(ForgeError, 'ASSET_NOT_FOUND'):
            self.registry.register(self.image, 'reference', 'unknown')

    def test_reference_image_read_only(self):
        data = self.image.read_bytes()
        result = self.registry.inspect_reference(self.image)
        self.assertEqual((result['width'], result['height']), (64, 96))
        self.assertEqual(result['visual_qa'], 'HUMAN_REVIEW_REQUIRED')
        self.assertEqual(self.image.read_bytes(), data)

    def test_snapshot_restore_preserves_single_state(self):
        self.registry.register(self.image, 'reference')
        snap = snapshot(self.forge)
        result = verify_restore(self.forge, snap['path'])
        self.assertEqual(result['restore_integrity'], 'ok')
        self.assertIn('assets', result['tables'])
        self.assertFalse(result['live_database_replaced'])
        self.assertEqual(len(self.registry.list()), 1)


if __name__ == '__main__':
    unittest.main()
