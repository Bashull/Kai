import tempfile
import unittest
from pathlib import Path

from kai_storage_commander.commander import StorageCommander, ExecutionBlocked


class FakeTransport:
    def __init__(self):
        self.calls = []

    def send(self, payload):
        self.calls.append(payload)
        return {"ok": True, "echo": payload}


class CommanderTests(unittest.TestCase):
    def make_commander(self):
        tmp = tempfile.TemporaryDirectory()
        transport = FakeTransport()
        commander = StorageCommander(transport=transport, audit_path=Path(tmp.name) / "audit.jsonl")
        self.addCleanup(tmp.cleanup)
        return commander, transport

    def test_mutating_request_plans_without_transport_execution(self):
        commander, transport = self.make_commander()
        result = commander.plan({"action": "move", "path": "/sdcard/A", "dest": "/sdcard/B"})
        self.assertEqual(transport.calls, [])
        self.assertTrue(result["plan"]["payload"]["dry_run"])

    def test_confirmed_execution_requires_matching_fingerprint(self):
        commander, transport = self.make_commander()
        planned = commander.plan({"action": "move", "path": "/sdcard/A", "dest": "/sdcard/B"})
        with self.assertRaises(ExecutionBlocked):
            commander.execute({"action": "move", "path": "/sdcard/A", "dest": "/sdcard/B", "confirm": True}, manifest_fingerprint="wrong")
        self.assertEqual(transport.calls, [])
        result = commander.execute({"action": "move", "path": "/sdcard/A", "dest": "/sdcard/B", "confirm": True}, manifest_fingerprint=planned["manifest_fingerprint"])
        self.assertTrue(result["response"]["ok"])
        self.assertEqual(len(transport.calls), 1)

    def test_result_never_claims_promoted_or_canonical(self):
        commander, _ = self.make_commander()
        result = commander.plan({"action": "list", "path": "/sdcard/Download"})
        serialized = str(result)
        self.assertNotIn("PROMOTED", serialized)
        self.assertNotIn("CANONICAL", serialized)


if __name__ == "__main__":
    unittest.main()
