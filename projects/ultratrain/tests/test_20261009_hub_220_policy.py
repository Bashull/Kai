import unittest

from projects.ultratrain.hub_220_policy import evaluate_hub_220
from projects.ultratrain.compatibility_core import Decision, evaluate_profile


class Hub220PolicyTests(unittest.TestCase):
    def test_streaming_metrics_requires_explicit_follow_on_220(self):
        finding = evaluate_hub_220({"packages": {"huggingface_hub": "2.2.0"}, "hub": {"jobs": {"metrics_mode": "stream"}}})
        self.assertEqual((finding.status, finding.rule), ("UNSUPPORTED", "hub.jobs.220_stream_requires_follow"))

    def test_streaming_metrics_explicit_follow_on_220(self):
        self.assertIsNone(evaluate_hub_220({"packages": {"huggingface_hub": "2.2.0"}, "hub": {"jobs": {"metrics_mode": "stream", "follow": True}}}))

    def test_snapshot_metrics_not_available_as_default_before_220(self):
        finding = evaluate_hub_220({"packages": {"huggingface_hub": "2.1.1"}, "hub": {"jobs": {"metrics_mode": "snapshot"}}})
        self.assertEqual(finding.status, "UNSUPPORTED")

    def test_legacy_concurrent_xet_downloads_need_canary(self):
        finding = evaluate_hub_220({"packages": {"huggingface_hub": "2.1.1"}, "hub": {"parallel_xet_downloads": True}})
        self.assertEqual((finding.status, finding.canary), ("NEEDS_CANARY", "hub_parallel_xet_integrity"))

    def test_220_concurrent_xet_downloads_do_not_infer_integrity(self):
        self.assertIsNone(evaluate_hub_220({"packages": {"huggingface_hub": "2.2.0"}, "hub": {"parallel_xet_downloads": True}}))

    def test_legacy_hffilesystem_refresh_needs_canary(self):
        finding = evaluate_hub_220({"packages": {"huggingface_hub": "2.1.1"}, "hub": {"filesystem_cache_refresh": True}})
        self.assertEqual((finding.status, finding.canary), ("NEEDS_CANARY", "hub_filesystem_cache_consistency"))

    def test_220_hffilesystem_refresh_does_not_need_legacy_canary(self):
        self.assertIsNone(evaluate_hub_220({"packages": {"huggingface_hub": "2.2.0"}, "hub": {"filesystem_cache_refresh": True}}))

    def test_unknown_version_does_not_get_implicit_support(self):
        finding = evaluate_hub_220({"hub": {"jobs": {"metrics_mode": "stream"}}})
        self.assertEqual((finding.status, finding.canary), ("NEEDS_CANARY", "hub_220_version_identity"))

    def test_unrelated_hub_profiles_are_unaffected(self):
        self.assertIsNone(evaluate_hub_220({"hub": {"xet": True}}))

    def test_core_blocks_220_streaming_without_follow(self):
        result = evaluate_profile({"profile_id": "hub220-stream", "packages": {"huggingface_hub": "2.2.0"}, "hub": {"jobs": {"metrics_mode": "stream"}}})
        self.assertEqual((result.status, result.rules), (Decision.UNSUPPORTED, ("hub.jobs.220_stream_requires_follow",)))

    def test_core_requires_legacy_xet_parallel_canary(self):
        result = evaluate_profile({"profile_id": "hub220-xet", "packages": {"huggingface_hub": "2.1.1"}, "hub": {"parallel_xet_downloads": True}})
        self.assertEqual(result.status, Decision.NEEDS_CANARY)
        self.assertIn("hub_parallel_xet_integrity", result.canaries)


if __name__ == "__main__":
    unittest.main()
