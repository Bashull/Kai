import importlib.util
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
PATH = BASE/'.agents/skills/kai-minecraft-cross-edition/scripts/route_mc.py'


class CrossEditionRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('route_mc', PATH)
        cls.router = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.router)

    def test_java_routes_to_java_adapter(self):
        plan = self.router.plan('java', 'paper', 'observe')
        self.assertEqual(plan['adapter'], 'mineflayer_mcp')
        self.assertFalse(plan['deployed'])
        self.assertEqual(plan['authorization'], 'required_before_live_actions')

    def test_native_bedrock_does_not_claim_mineflayer(self):
        plan = self.router.plan('bedrock', 'bedrock-dedicated', 'move')
        self.assertEqual(plan['adapter'], 'bedrock_protocol_candidate')
        self.assertTrue(plan['needs_server_test'])
        self.assertNotIn('mineflayer_mcp', plan['adapter'])

    def test_geyser_is_java_host_with_crossplay(self):
        plan = self.router.plan('crossplay', 'geyser-java', 'npc')
        self.assertEqual(plan['adapter'], 'mineflayer_mcp')
        self.assertTrue(plan['geyser_translation'])
        self.assertIn('not a native Bedrock bot', plan['warning'])

    def test_unknown_server_is_inspection_only(self):
        plan = self.router.plan('unknown', 'unknown', 'voice')
        self.assertEqual(plan['adapter'], 'none')
        self.assertEqual(plan['next_step'], 'identify_server_edition_software_version')

    def test_invalid_combinations_rejected(self):
        with self.assertRaises(ValueError):
            self.router.plan('java', 'bedrock-dedicated', 'build')
        with self.assertRaises(ValueError):
            self.router.plan('bedrock', 'paper', 'build')
        with self.assertRaises(ValueError):
            self.router.plan('java', 'paper', 'arbitrary_shell')

    def test_research_router_never_claims_deployment(self):
        for edition, server in [('java','paper'),('bedrock','bedrock-dedicated'),('crossplay','geyser-java'),('unknown','unknown')]:
            out = self.router.plan(edition, server, 'chat')
            self.assertFalse(out['deployed'])
            self.assertTrue(out['dry_run_only'])

    def test_router_skill_manifest_is_discoverable_by_codex(self):
        skill = BASE/'.agents/skills/kai-minecraft-cross-edition/SKILL.md'
        content = skill.read_text(encoding='utf-8')
        self.assertIn('name: kai-minecraft-cross-edition', content)
        self.assertIn('--edition', content)
        self.assertIn('dry-run', content)

    def test_bedrock_java_mismatch_fails_closed(self):
        with self.assertRaises(ValueError):
            self.router.plan('crossplay', 'bedrock-dedicated', 'chat')

if __name__ == '__main__':
    unittest.main()
