import json
import tempfile
import unittest
from pathlib import Path

from audio_studio.manifests import ManifestError, ManifestStore
from audio_studio.models import Availability, CapabilitySnapshot, SongRequest
from audio_studio.providers import AceStepAdapter, MiniMaxMusic3Adapter, SunoV55Adapter


def snapshot(name):
    return CapabilitySnapshot(
        provider_id=name,
        availability=Availability.AVAILABLE,
        capabilities=frozenset({"text_to_music"}),
        cost_class="FREE",
        runtime="REMOTE",
    )


class CompilerTests(unittest.TestCase):
    def setUp(self):
        self.request = SongRequest("case-1", {
            "core_identity": "EDM, 128 BPM",
            "emotional_arc": "intimate to euphoric",
            "vocal_identity": "female lead",
            "arrangement": "pads enter, full drop, piano outro",
            "lyrics": "[Chorus]\nFly",
            "avoid": ["shouting"],
            "duration_seconds": 180,
            "seed": 42,
        })
    def test_ace_compiles_caption_and_native_fields(self):
        out = AceStepAdapter("ace", snapshot("ace")).compile(self.request)
        self.assertIn("EDM", out["prompt"])
        self.assertEqual(out["seed"], 42)
        self.assertFalse(out["use_random_seed"])
        self.assertFalse(out["use_format"])

    def test_minimax_separates_prompt_layers(self):
        out = MiniMaxMusic3Adapter("minimax", snapshot("minimax")).compile(self.request)
        self.assertEqual(out["model"], "music-3.0")
        self.assertIn("female lead", out["prompt"])
        self.assertIn("piano outro", out["prompt"])

    def test_suno_separates_style_lyrics_and_exclude(self):
        out = SunoV55Adapter("suno", snapshot("suno")).compile(self.request)
        self.assertFalse(out["executable"])
        self.assertEqual(out["contract_status"], "UNVERIFIED_AUTH_REQUIRED")
        self.assertEqual(out["blueprint_draft"]["lyrics"], "[Chorus]\nFly")
        self.assertEqual(out["blueprint_draft"]["exclude"], ["shouting"])


class ManifestStoreTests(unittest.TestCase):
    def valid_manifest(self):
        return {
            "schema_version": "1.0.0", "case_id": "case-1", "status": "READY",
            "blueprint": {}, "provider": {}, "generation": {},
            "assets": [], "evidence": {},
        }
    def test_loads_valid_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "manifest.json"
            path.write_text(json.dumps(self.valid_manifest()), encoding="utf-8")
            manifest = ManifestStore(root).load(path)
            self.assertEqual(manifest.case_id, "case-1")

    def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as outside:
            root = Path(td)
            path = Path(outside) / "manifest.json"
            path.write_text(json.dumps(self.valid_manifest()), encoding="utf-8")
            with self.assertRaisesRegex(ManifestError, "escapes"):
                ManifestStore(root).load(path)

    def test_rejects_incomplete_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "manifest.json"
            path.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ManifestError, "missing fields"):
                ManifestStore(root).load(path)


if __name__ == "__main__":
    unittest.main()
