import tempfile
import unittest
from pathlib import Path

from core.loop_factory.errors import LoopFactoryError
from core.loop_factory.model import ErrorClass
from core.loop_factory.guards import assert_noncanonical_branch, assert_write_scope


class GuardTests(unittest.TestCase):
    def test_main_and_master_fail_closed(self):
        for branch in ("main", "master"):
            with self.assertRaises(LoopFactoryError) as ctx:
                assert_noncanonical_branch(branch)
            self.assertEqual(ctx.exception.error_class, ErrorClass.CANONICAL_BRANCH_GUARD)

    def test_feature_branch_is_allowed(self):
        assert_noncanonical_branch("feat/loop-factory-cell-000")

    def test_out_of_scope_target_is_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root / "main.py"
            with self.assertRaises(LoopFactoryError) as ctx:
                assert_write_scope(outside, [root / "sandbox"])
            self.assertEqual(ctx.exception.error_class, ErrorClass.WRITE_SCOPE_VIOLATION)
            self.assertFalse(outside.exists())

from core.loop_factory.model import AutonomyLevel, Budget, JobManifest
from core.loop_factory.policy import ActionRequest, PolicyEngine


class PolicyTests(unittest.TestCase):
    def make_job(self, level=AutonomyLevel.A2, max_cost=0.0):
        return JobManifest.new(
            job_id="policy-test",
            project="KAI_LOOP_FACTORY",
            cell_type="BUILD",
            goal="policy test",
            write_scope=["/tmp/kai-sandbox"],
            autonomy_level=level,
            allowed_tools=["demo-file"],
            budget=Budget(max_cost_eur=max_cost, max_iterations=2, max_retries=1, timeout_seconds=30),
        )

    def test_cost_above_budget_is_denied(self):
        decision = PolicyEngine().evaluate(
            self.make_job(max_cost=0.0),
            ActionRequest(name="gpu", estimated_cost_eur=0.01),
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.error_class, ErrorClass.BUDGET_EXCEEDED)

    def test_promotion_requires_explicit_authorization(self):
        decision = PolicyEngine().evaluate(
            self.make_job(level=AutonomyLevel.A4),
            ActionRequest(
                name="merge",
                required_level=AutonomyLevel.A4,
                promotion=True,
                mutation=True,
                target_branch="feat/candidate",
            ),
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.error_class, ErrorClass.AUTH_REQUIRED)

    def test_security_action_never_self_authorizes(self):
        job = self.make_job(level=AutonomyLevel.A5)
        action = ActionRequest(
            name="rotate-secret",
            required_level=AutonomyLevel.A5,
            security_sensitive=True,
            mutation=True,
        )
        self.assertFalse(PolicyEngine().evaluate(job, action).allowed)
        self.assertTrue(PolicyEngine().evaluate(job, action, explicit_authorization=True).allowed)
