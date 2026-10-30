"""Synthetic tests for 2026-10-30 candidate gates. No GPU/runtime attestation."""
import unittest
from projects.ultratrain.release_20261030_policy import findings_release_20261030

def rules(profile):
    return {x["rule"]: x["status"] for x in findings_release_20261030(profile)}

class Release1030Candidate(unittest.TestCase):
    def test_inert(self):
        self.assertEqual(findings_release_20261030({}), [])
    def test_malformed(self):
        self.assertIn("release1030.profile_shape", rules({"runtime": []}))
    def test_megatron_batch_variant(self):
        p = {"training": {"backend": "megatron_core", "tensor_parallel_size": 4},
             "rl": {"vocab_parallel_logprobs": True, "batch_invariant_mode": True,
                    "reduction_algorithm": "nccl_sum_order"}}
        self.assertEqual(rules(p)["megatron.rl.batch_variant_reduction"], "UNSUPPORTED")
    def test_megatron_needs_evidence(self):
        p = {"training": {"backend": "megatron_core", "tensor_parallel_size": 4},
             "rl": {"vocab_parallel_logprobs": True, "batch_invariant_mode": True}}
        self.assertIn("megatron.rl.batch_invariant_canary", rules(p))
        self.assertIn("megatron.rl.backward_parity", rules(p))
    def test_megatron_merge_not_attestation(self):
        p = {"training": {"backend": "megatron"},
             "rl": {"vocab_parallel_logprobs": True, "trust_merely_merged_pr": True}}
        self.assertEqual(rules(p)["megatron.rl.merged_not_runtime_attestation"], "UNSUPPORTED")
    def test_sglang_retraction_penalty(self):
        p = {"packages": {"sglang": "0.5.22"}, "runtime": {"provider": "sglang"},
             "sampling": {"frequency_penalty": 2}}
        self.assertEqual(rules(p)["sglang.1030.retraction_sampling_history_reset"], "UNSUPPORTED")
    def test_sglang_retraction_min_tokens(self):
        p = {"packages": {"sglang": "0.5.22"}, "runtime": {"provider": "sglang"},
             "sampling": {"min_new_tokens": 8}}
        self.assertIn("sglang.1030.retraction_sampling_history_reset", rules(p))
    def test_sglang_pd_gap(self):
        p = {"runtime": {"provider": "sglang", "pd_disaggregation": True},
             "sampling": {"penalties_enabled": True}}
        self.assertIn("sglang.1030.pd_prebuilt_retraction_gap", rules(p))
    def test_profile_unbounded(self):
        p = {"runtime": {"provider": "sglang"},
             "profiling": {"endpoint_enabled": True, "profile_by_stage": True}}
        self.assertEqual(rules(p)["sglang.1030.stage_profile_unbounded_crash"], "UNSUPPORTED")
    def test_profile_public(self):
        p = {"runtime": {"provider": "sglang"},
             "profiling": {"endpoint_enabled": True, "network_access": "public"}}
        self.assertEqual(rules(p)["sglang.1030.profiling_endpoint_exposed"], "UNSUPPORTED")
    def test_vllm_open_pr(self):
        p = {"runtime": {"provider": "vllm", "flashinfer_allreduce": True,
                         "pdl_enabled": True, "small_oneshot_possible": True,
                         "assume_pr_64420_shipped": True}}
        self.assertIn("vllm.1030.flashinfer_pdl_completion_race", rules(p))
        self.assertEqual(rules(p)["vllm.1030.open_pr_not_release"], "UNSUPPORTED")
    def test_deterministic(self):
        p = {"runtime": {"provider": "sglang"},
             "profiling": {"endpoint_enabled": True, "profile_by_stage": True}}
        self.assertEqual(findings_release_20261030(p), findings_release_20261030(p))

if __name__ == "__main__":
    unittest.main()
