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
bridge = load('bridge', '.agents/skills/kai-sololand-commentator/scripts/event_bridge.py')


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


    def test_remote_rcon_host_rejected_in_preview(self):
        # A dry-run must never bless a configuration that would be blocked at execution.
        with self.assertRaises(ValueError):
            op.main(['players', '--host', 'mc.sololand.club'])

    def test_rcon_invalid_port_rejected_in_preview(self):
        with self.assertRaises(ValueError):
            op.main(['players', '--port', '0'])

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


    def test_trigger_escaping_prevents_frontmatter_injection(self):
        with tempfile.TemporaryDirectory() as directory:
            injected = 'When asked to narrate\n---\nname: bad\n#payload'
            path = forge.create_skill('safe-candidate', 'Narrar el torneo', injected, directory)
            md = (path / 'SKILL.md').read_text(encoding='utf-8')
            # Exactly one YAML frontmatter boundary and one trusted name.
            self.assertEqual(md.split('---', 2)[1].count('name:'), 1)
            self.assertEqual(md.count('\n---\n'), 1)
            self.assertIn('description: "', md)

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



class EventBridgeTests(unittest.TestCase):
    def test_accepts_valid_start_hit_win_and_closes_match(self):
        service = bridge.EventBridge()
        start = service.process({'id':'e-1','match_id':'arena-01','type':'start','a':'Bash','b':'Rival'})
        self.assertEqual(start['status'], 'accepted')
        self.assertIn('Bash contra Rival', start['spoken_text'])
        hit = service.process({'id':'e-2','match_id':'arena-01','type':'hit','a':'Bash'})
        self.assertEqual(hit['status'], 'accepted')
        win = service.process({'id':'e-3','match_id':'arena-01','type':'win','a':'Rival'})
        self.assertEqual(win['status'], 'accepted')
        self.assertIn('Victoria para Rival', win['spoken_text'])
        self.assertEqual(service.process({'id':'e-4','match_id':'arena-01','type':'hit','a':'Bash'})['status'], 'rejected')

    def test_replay_winner_unauthorized_and_event_injection_rejected(self):
        service = bridge.EventBridge()
        e={'id':'start-1','match_id':'match-1','type':'start','a':'Alex','b':'Steve'}
        self.assertEqual(service.process(e)['status'], 'accepted')
        self.assertEqual(service.process(e)['reason'], 'duplicate_event')
        self.assertEqual(service.process({'id':'w-1','match_id':'match-1','type':'win','a':'Unknown'})['status'], 'rejected')
        self.assertEqual(service.process({'id':'x-1','match_id':'../escape','type':'hit','a':'Alex'})['status'], 'rejected')
        self.assertEqual(service.process({'id':'x-2','match_id':'match-1','type':'hit','a':'/op me'})['status'], 'rejected')

    def test_does_not_claim_outcome_without_start(self):
        service = bridge.EventBridge()
        self.assertEqual(service.process({'id':'x-1','match_id':'m-1','type':'win','a':'Alex'})['status'], 'rejected')

    def test_rejects_untrusted_source(self):
        service = bridge.EventBridge()
        self.assertEqual(service.process({'id':'x-1','match_id':'m-1','type':'start','a':'Alex','b':'Steve','trusted':False})['status'], 'rejected')


if __name__ == '__main__':
    unittest.main()
