"""A recovery tick may observe existing work, but cannot create paid work."""
import unittest

from kai_meshy.core import ForgeError
from kai_meshy.operation_loop import cycle_operations


class Observations:
    def __init__(self, statuses, *, rejected=False, cancelled=False):
        self.forge = self
        self.statuses = statuses
        self.rejected, self.cancelled = rejected, cancelled
        self.observed = []

    def get_job(self, job):
        return {'job': {'rejected': self.rejected, 'local_cancelled': self.cancelled}}

    def list_operations(self, job):
        return [{'operation_id': str(i), 'status': status} for i, status in enumerate(self.statuses)]

    def refresh_operation(self, job, operation, *, timeout=None):
        self.observed.append(operation)
        if operation == '2':
            raise ForgeError('READ_TRANSPORT_INTERRUPTED')
        return {'status': 'SUCCEEDED'}


class OperationLoopTests(unittest.TestCase):
    def test_unknown_and_planned_never_trigger_remote_work(self):
        engine = Observations(['PLANNED', 'SUBMISSION_UNKNOWN', 'SUCCEEDED', 'FAILED'])
        result = cycle_operations(engine, 'job')
        self.assertEqual(engine.observed, [])
        self.assertFalse(result['paid_submission_performed'])
        self.assertEqual(result['operations'][1]['next_action'], 'RECONCILE_ORIGINAL_REQUEST_NEVER_REPEAT_POST')
        self.assertEqual(result['operations'][2]['next_action'], 'RECOVER_EXISTING_OUTPUT')

    def test_one_pass_retains_identity_on_failed_observation(self):
        engine = Observations(['PENDING', 'IN_PROGRESS', 'PENDING'])
        result = cycle_operations(engine, 'job')
        self.assertEqual(engine.observed, ['0', '1', '2'])
        self.assertEqual(result['operations'][2]['status'], 'PENDING')
        self.assertEqual(result['operations'][2]['next_action'], 'RETRY_READ_ONLY_OBSERVATION')
        self.assertEqual(result['max_attempts_per_operation'], 1)

    def test_stop_and_rejection_do_not_observe(self):
        for kwargs in ({'rejected': True}, {'cancelled': True}):
            engine = Observations(['PENDING'], **kwargs)
            result = cycle_operations(engine, 'job')
            self.assertEqual(engine.observed, [])
            self.assertFalse(result['paid_submission_performed'])

    def test_limit_bounds_pass_and_invalid_limits_deny(self):
        engine = Observations(['PENDING'] * 10)
        result = cycle_operations(engine, 'job', max_operations=1)
        self.assertEqual(engine.observed, ['0'])
        self.assertEqual(result['remaining'], 9)
        for kwargs in ({'timeout': True}, {'timeout': 31}, {'timeout': 0}, {'max_operations': True}, {'max_operations': 51}):
            with self.assertRaises(ForgeError):
                cycle_operations(engine, 'job', **kwargs)


if __name__ == '__main__':
    unittest.main()
