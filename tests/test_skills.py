import importlib.util
import json
import socket
import struct
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


op = load('operator', '.agents/skills/kai-minecraft-pc/scripts/mc_operator.py')
forge = load('forge', '.agents/skills/kai-minecraft-skill-forge/scripts/forge_skill.py')
comment = load('comment', '.agents/skills/kai-sololand-commentator/scripts/commentary.py')


class OperatorTests(unittest.TestCase):
    def test_message_normal(self):
        self.assertEqual(op.validate_message('Buenas'), '[Kai] Buenas')

    def test_message_rejects_commands(self):
        for s in ['/op me', 'hola\nstop', '', 'x'*181]:
            with self.assertRaises(ValueError):
                op.validate_message(s)

    def test_rcon_local_only_and_no_secret(self):
        with self.assertRaises(ValueError):
            op.run_rcon('mc.sololand.club', 25575, 'password', 'list')
        with self.assertRaises(ValueError):
            op.run_rcon('127.0.0.1', 25575, '', 'list')

    def test_rcon_binary_packet(self):
        packed = op.rcon_packet(3, 2, 'list')
        self.assertEqual(struct.unpack('<i', packed[:4])[0], len(packed)-4)
        self.assertEqual(struct.unpack('<ii', packed[4:12]), (3, 2))
        self.assertTrue(packed.endswith(b'list\0\0'))

    def test_packet_short_read(self):
        class Sock:
            data = [b'abc', b'de']
            def recv(self, n):
                return self.data.pop(0) if self.data else b''
        self.assertEqual(op.recv_exact(Sock(), 5), b'abcde')

    def test_gui_not_minecraft_denied(self):
        old = op.active_mc_window
        try:
            op.active_mc_window = lambda: 'Minecraft Java Edition'
            with self.assertRaises(ValueError):
                op.gui_action('key', 'delete', False)
            self.assertEqual(op.gui_action('key', 'w', False)['status'], 'dry_run')
        finally:
            op.active_mc_window = old


class ForgeTests(unittest.TestCase):
    def test_create_no_overwrite(self):
        with tempfile.TemporaryDirectory() as dir:
            p = forge.create_skill('minecraft-test-safe', 'Example purpose', 'When testing in staging', dir)
            self.assertTrue((p/'SKILL.md').is_file())
            self.assertEqual(json.loads((p/'manifest.json').read_text())['state'], 'CANDIDATE')
            with self.assertRaises(FileExistsError):
                forge.create_skill('minecraft-test-safe', 'Purpose', 'Trigger', dir)

    def test_reject_path_traversal(self):
        with tempfile.TemporaryDirectory() as dir:
            for slug in ('../bad', 'CamelName', ' bad ', '.hidden'):
                with self.assertRaises(ValueError):
                    forge.create_skill(slug, 'Purpose', 'Trigger', dir)


class CommentaryTests(unittest.TestCase):
    def test_offline_start_and_win(self):
        self.assertIn('Alex contra Steve', comment.call('start', 'Alex', 'Steve'))
        self.assertIn('Victoria para Alex', comment.call('win', 'Alex'))

    def test_bad_event_and_identity(self):
        with self.assertRaises(ValueError):
            comment.call('ban', 'Alex')
        with self.assertRaises(ValueError):
            comment.call('win', '../user')


if __name__ == '__main__':
    unittest.main()
