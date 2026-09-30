import unittest

from projects.ultratrain.hub_security_policy import evaluate_hub_policy


class HubSecurityPolicyTests(unittest.TestCase):
    def test_untrusted_pickle_loading_is_blocked(self):
        r = evaluate_hub_policy({"hub": {"untrusted_torch_checkpoint": True, "safe_serialization": False}})
        self.assertFalse(r.allowed)
        self.assertEqual(r.rule, "hub.serialization.safe_loader_required")

    def test_shared_blobs_require_hub_132(self):
        r = evaluate_hub_policy({"hub": {"shared_xet_blobs": True}, "packages": {"huggingface_hub": "1.31.0"}})
        self.assertFalse(r.allowed)
        self.assertEqual(r.rule, "hub.shared_blobs.requires_1_32")

    def test_shared_blobs_require_roundtrip_canary(self):
        r = evaluate_hub_policy({"hub": {"shared_xet_blobs": True}, "packages": {"huggingface_hub": "1.32.0"}})
        self.assertTrue(r.needs_canary)

    def test_parent_segments_are_rejected(self):
        r = evaluate_hub_policy({"hub": {"path_in_repo_contains_parent_segment": True}})
        self.assertFalse(r.allowed)
        self.assertEqual(r.rule, "hub.path_traversal.reject_parent_segments")

    def test_hardened_profile_is_supported(self):
        r = evaluate_hub_policy({"hub": {"shared_xet_blobs": True, "shared_blob_canary_passed": True}, "packages": {"huggingface_hub": "1.32.0"}})
        self.assertTrue(r.allowed)


if __name__ == "__main__":
    unittest.main()
