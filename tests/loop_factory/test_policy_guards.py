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
