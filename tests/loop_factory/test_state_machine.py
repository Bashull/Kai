import unittest

from core.loop_factory.errors import LoopFactoryError
from core.loop_factory.model import JobState
from core.loop_factory.state_machine import assert_transition, is_terminal


class StateMachineTests(unittest.TestCase):
    def test_happy_path_is_legal(self):
        path = [
            JobState.QUEUED,
            JobState.READY,
            JobState.RUNNING,
            JobState.VERIFYING,
            JobState.CHECKPOINTED,
            JobState.SUCCEEDED,
        ]
        for current, target in zip(path, path[1:]):
            assert_transition(current, target)

    def test_terminal_attempt_has_no_outgoing_transition(self):
        self.assertTrue(is_terminal(JobState.SUCCEEDED))
        with self.assertRaises(LoopFactoryError):
            assert_transition(JobState.SUCCEEDED, JobState.RUNNING)

    def test_recoverable_attempt_can_request_requeue(self):
        assert_transition(JobState.RUNNING, JobState.REQUEUE)
