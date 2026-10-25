import unittest
from projects.ultratrain.inspect_03283_candidate import inspect_03283_findings as check

class Inspect283CandidateTests(unittest.TestCase):
    def base(self, version="0.3.283"):
        return {"packages": {"inspect_ai": version}, "evaluation": {"engine": "inspect_ai"}}
    def rules(self, p):
        return {f["rule"]: f["status"] for f in check(p)}
    def test_reserved_collision(self):
        p = self.base()
        p["inspect_dataset"] = {"fields": ["checkpoint"], "checkpoint_meaning": "unrelated"}
        self.assertEqual(self.rules(p)["inspect.03283.reserved_checkpoint_collision"], "UNSUPPORTED")
    def test_reserved_override(self):
        p = self.base()
        p["inspect_dataset"] = {"fields": ["checkpoint"], "checkpoint_meaning": "unrelated", "fieldspec_checkpoint_none": True}
        self.assertNotIn("inspect.03283.reserved_checkpoint_collision", self.rules(p))
    def test_prepatch_evalset(self):
        p = self.base("0.3.282")
        p["inspect_resume"] = {"mode": "eval_set", "log_trust": "shared"}
        self.assertEqual(self.rules(p)["inspect.pre03283.eval_set_log_sandbox_injection"], "UNSUPPORTED")
    def test_evalretry_untrusted_still_blocked(self):
        p = self.base()
        p["inspect_resume"] = {"mode": "eval_retry", "log_trust": "untrusted"}
        self.assertEqual(self.rules(p)["inspect.03283.eval_retry_untrusted_log_sandbox"], "UNSUPPORTED")
    def test_mixed_samples_without_provenance(self):
        p = self.base()
        p["inspect_resume"] = {"mode": "eval_set", "mixed_sandbox_samples": True}
        self.assertEqual(self.rules(p)["inspect.03283.mixed_sandbox_provenance_missing"], "UNSUPPORTED")
    def test_no_side_effects_or_auto_approval(self):
        self.assertEqual(check({}), [])
