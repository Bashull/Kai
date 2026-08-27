import json
import tempfile
import unittest
from pathlib import Path

from audio_studio.models import Availability, CapabilitySnapshot, SongRequest
from audio_studio.providers import AceMusicCompletionAdapter
from audio_studio.runtime_termux import credential_present


class TermuxCloudTests(unittest.TestCase):
    def snapshot(self):
        return CapabilitySnapshot(
            provider_id="ace-step-1.5-cloud",
            availability=Availability.AVAILABLE,
            capabilities=frozenset({"text_to_music"}),
            cost_class="UNKNOWN",
            runtime="REMOTE",
        )

    def test_completion_compiler_matches_verified_client_contract(self):
        request = SongRequest("case", {
            "core_identity": "festival EDM",
            "emotional_arc": "rising",
            "lyrics": "[Chorus]\nFly",
            "duration_seconds": 210,
            "bpm": 134,
            "seed": 42,
        })
        out = AceMusicCompletionAdapter(
            "ace-step-1.5-cloud", self.snapshot()
        ).compile(request)
        self.assertEqual(out["model"], "acemusic/acestep-v1.5-turbo")
        self.assertEqual(out["messages"][0]["role"], "user")
        self.assertIn("<prompt>", out["messages"][0]["content"])
        self.assertIn("<lyrics>[Chorus]\nFly</lyrics>", out["messages"][0]["content"])
        self.assertEqual(out["audio_config"]["duration"], 210)
        self.assertEqual(out["audio_config"]["bpm"], 134)
        self.assertEqual(out["seed"], 42)
        self.assertFalse(out["stream"])

    def test_credential_resolver_returns_presence_only(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            path = home / ".agents/skills/acestep/scripts"
            path.mkdir(parents=True)
            (path / "config.json").write_text(
                json.dumps({"api_key": "never-return-this"}),
                encoding="utf-8",
            )
            result = credential_present(
                "termux:~/.agents/skills/acestep/scripts/config.json#api_key",
                home=home,
            )
            self.assertIs(result, True)

    def test_credential_resolver_rejects_unknown_pointer(self):
        with self.assertRaisesRegex(ValueError, "unsupported"):
            credential_present("termux:~/other.json#api_key")


if __name__ == "__main__":
    unittest.main()
