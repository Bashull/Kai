import unittest

from kai_storage_commander.manifest import build_manifest, fingerprint_manifest, verify_manifest_fingerprint


class ManifestTests(unittest.TestCase):
    def test_manifest_fingerprint_is_deterministic(self):
        request = {"action": "move", "path": "/sdcard/A", "dest": "/sdcard/B", "dry_run": True, "confirm": False}
        first = fingerprint_manifest(build_manifest(request))
        second = fingerprint_manifest(build_manifest(dict(reversed(list(request.items())))))
        self.assertEqual(first, second)

    def test_changed_request_fails_fingerprint_verification(self):
        original = build_manifest({"action": "move", "path": "/sdcard/A", "dest": "/sdcard/B", "dry_run": True, "confirm": False})
        fingerprint = fingerprint_manifest(original)
        changed = build_manifest({"action": "move", "path": "/sdcard/A", "dest": "/sdcard/C", "dry_run": True, "confirm": False})
        self.assertFalse(verify_manifest_fingerprint(changed, fingerprint))


if __name__ == "__main__":
    unittest.main()
