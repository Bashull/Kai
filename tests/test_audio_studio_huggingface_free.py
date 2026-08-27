import unittest

from audio_studio.execution import authorize_execution
from audio_studio.models import SongRequest
from audio_studio.planning import plan_dry_run
from audio_studio.runtime_huggingface import build_zerogpu_provider


class HuggingFaceFreeRouteTests(unittest.TestCase):
    def reader(self, url):
        self.assertTrue(url.endswith("/config"))
        return 200, {
            "version": "6.2.0",
            "api_prefix": "/gradio_api",
            "root": "https://ace-step-ace-step-v1-5.hf.space",
        }

    def test_free_limited_route_plans_without_generation(self):
        provider = build_zerogpu_provider(self.reader)
        request = SongRequest("free-case", {
            "core_identity": "uplifting EDM",
            "lyrics": "[Chorus]\nFly",
            "duration_seconds": 120,
            "seed": 42,
        })
        report = plan_dry_run(request, [provider])
        self.assertEqual(report.status, "PLANNED")
        self.assertEqual(report.selected_provider, "ace-step-1.5-zerogpu")
        self.assertFalse(report.generation_attempted)
        snapshot = provider.probe()
        self.assertTrue(authorize_execution(snapshot).allowed)
        self.assertEqual(snapshot.evidence["quota_class"], "DAILY_ZEROGPU_QUOTA")

    def test_wrong_space_identity_is_rejected(self):
        provider = build_zerogpu_provider(lambda url: (200, {
            "version": "6.2.0",
            "api_prefix": "/gradio_api",
            "root": "https://wrong.example",
        }))
        self.assertEqual(provider.probe().availability.value, "OFFLINE")


if __name__ == "__main__":
    unittest.main()
