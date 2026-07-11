import json
import tempfile
import unittest
from pathlib import Path

from kai_storage_commander.audit import AuditWriter
from kai_storage_commander.transport import HttpStorageTransport, build_http_payload


class AuditTransportTests(unittest.TestCase):
    def test_audit_redacts_secret_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            writer = AuditWriter(path)
            writer.append({"action": "health", "token": "super-secret", "authorization": "Bearer abc"})
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("super-secret", text)
            self.assertNotIn("Bearer abc", text)
            self.assertIn("[REDACTED]", text)

    def test_audit_is_append_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            writer = AuditWriter(path)
            writer.append({"event": 1})
            writer.append({"event": 2})
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[0])["event"], 1)
            self.assertEqual(json.loads(lines[1])["event"], 2)

    def test_http_payload_uses_only_agent_fields(self):
        payload = build_http_payload({"action": "list", "path": "/sdcard/Download", "status": "VALIDATED_LOCAL_CANDIDATE", "token": "x"})
        self.assertEqual(payload, {"action": "list", "path": "/sdcard/Download"})

    def test_http_transport_rejects_non_loopback_url(self):
        with self.assertRaises(ValueError):
            HttpStorageTransport("https://evil.example", token="secret")

    def test_http_transport_requires_token(self):
        with self.assertRaises(ValueError):
            HttpStorageTransport("http://127.0.0.1:8787", token="")


if __name__ == "__main__":
    unittest.main()
