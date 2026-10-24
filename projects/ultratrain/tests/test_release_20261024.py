"""Offline synthetic regression for the 2026-10-24 candidate gate."""
import unittest
from projects.ultratrain.release_20261024_policy import findings_release_20261024

def rules(profile):
    return {f["rule"]: f["status"] for f in findings_release_20261024(profile)}

class Release20261024Tests(unittest.TestCase):
    def test_inert(self):
        self.assertEqual(findings_release_20261024({}), [])

    def test_shape(self):
        self.assertIn("release.1024.profile_shape", rules({"hub": []}))

    def test_hub_old_silent_loss(self):
        p = {"packages": {"huggingface_hub": "2.2.0"},
             "hub": {"delete_and_readd": True, "readd_unchanged_files": True}}
        self.assertEqual(rules(p)["hub.pre230.delete_readd_silent_loss"], "UNSUPPORTED")

    def test_hub_fixed_still_canary(self):
        p = {"packages": {"huggingface_hub": "2.3.0"},
             "hub": {"delete_and_readd": True, "readd_unchanged_files": True}}
        self.assertEqual(rules(p)["hub.230.delete_readd_integrity"], "NEEDS_CANARY")

    def test_destructive_manifest_rollback(self):
        r = rules({"hub": {"destructive_commit": True}})
        self.assertIn("hub.230.post_commit_manifest_required", r)
        self.assertIn("hub.230.rollback_snapshot_required", r)

    def test_version_conflict(self):
        p = {"packages": {"huggingface_hub": "2.3.0"},
             "hub": {"create_commit": True, "version": "2.2.0"}}
        self.assertIn("hub.230.version_identity", rules(p))

    def test_live_follow_repo_block(self):
        p = {"packages": {"huggingface_hub": "2.3.0"},
             "hub": {"live_follow": True, "target_kind": "dataset_repo"}}
        self.assertEqual(rules(p)["hub.230.live_follow_buckets_only"], "UNSUPPORTED")

    def test_live_follow_old_version_block(self):
        p = {"packages": {"huggingface_hub": "2.2.0"},
             "hub": {"live_follow": True, "target_kind": "bucket"}}
        self.assertEqual(rules(p)["hub.pre230.live_follow_unavailable"], "UNSUPPORTED")

    def test_live_follow_budget(self):
        p = {"packages": {"huggingface_hub": "2.3.0"},
             "hub": {"live_follow": True, "target_kind": "bucket"}}
        self.assertIn("hub.230.live_follow_connection_budget", rules(p))

    def test_listing_workers(self):
        p = {"packages": {"huggingface_hub": "2.3.0"},
             "hub": {"recursive_listing": True, "max_workers": 9999}}
        self.assertEqual(rules(p)["hub.230.listing_workers_invalid"], "UNSUPPORTED")

    def test_bulk_metadata_main_only(self):
        p = {"packages": {"huggingface_hub": "2.3.0"},
             "hub": {"sharded_safetensors_bulk_metadata": True, "revision": "sha"}}
        self.assertEqual(rules(p)["hub.230.bulk_shard_metadata_main_only"], "UNSUPPORTED")

    def test_jobs_logs(self):
        p = {"hub": {"hf_jobs_run": True, "trust_cli_log_end_as_completion": True}}
        self.assertEqual(rules(p)["hub.230.job_logs_not_completion_proof"], "UNSUPPORTED")

    def test_sglang_exposed_old(self):
        p = {"packages": {"sglang": "0.5.22"},
             "runtime": {"sglang": True, "network_exposure": "public", "multi_tenant": True}}
        self.assertEqual(rules(p)["sglang.112266.exposed_affected_version"], "UNSUPPORTED")

    def test_sglang_unknown_patch(self):
        p = {"packages": {"sglang": "0.5.23"},
             "runtime": {"sglang": True, "network_exposure": "public", "multi_tenant": True}}
        self.assertEqual(rules(p)["sglang.112266.fix_unverified"], "NEEDS_CANARY")

    def test_sglang_cross_tenant_rid(self):
        p = {"runtime": {"sglang": True, "multi_tenant": True, "client_rid_forwarded": True}}
        self.assertEqual(rules(p)["sglang.112266.cross_tenant_rid_abort"], "UNSUPPORTED")

    def test_sglang_owner_auth(self):
        p = {"runtime": {"sglang": True, "multi_tenant": True,
                         "client_rid_forwarded": True, "tenant_scoped_cancel_authorized": True}}
        self.assertNotIn("sglang.112266.cross_tenant_rid_abort", rules(p))

    def test_sglang_unknown_version(self):
        p = {"runtime": {"sglang": True, "multi_tenant": True, "network_exposure": "public"}}
        self.assertIn("sglang.112266.version_identity", rules(p))

if __name__ == "__main__":
    unittest.main()
