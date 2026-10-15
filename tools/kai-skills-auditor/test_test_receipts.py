"""Receipt acceptance checks use synthetic sources, never the historical build."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from run_tool_checks import CountedResult, run_checks, source_hashes, tool_test_evidence, validate_receipt


class TestReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='kai-tool-receipt-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root/'tools'
        self.source.mkdir()
        (self.source/'example.py').write_text('VALUE = 1\n')
        self.path = self.root/'receipt.json'
        self.good = {
            'format': 'kai.skills.tool-tests/1', 'status': 'PASS',
            'tests_run': 3, 'passed': 2, 'skipped': 1, 'failures': 0, 'errors': 0,
            'expected_failures': 0, 'unexpected_successes': 0, 'exit_code': 0,
            'source_unchanged': True, 'source_sha256': source_hashes(self.source),
        }

    def save(self, receipt=None):
        self.path.write_text(json.dumps(self.good if receipt is None else receipt))

    def test_no_receipt_is_not_run_never_an_inherited_pass(self):
        stats, receipt = tool_test_evidence(None, self.source)
        self.assertIsNone(receipt)
        self.assertEqual(stats['tool_regression_tests'], 0)
        self.assertEqual(stats['tool_regression_tests_passed'], 0)
        self.assertEqual(stats['tool_regression_tests_status'], 'NOT_RUN')

    def test_valid_receipt_accepts_current_source_and_separates_skips(self):
        self.save()
        stats, receipt = tool_test_evidence(self.path, self.source)
        self.assertEqual(receipt, self.good)
        self.assertEqual(stats['tool_regression_tests'], 3)
        self.assertEqual(stats['tool_regression_tests_executed'], 2)
        self.assertEqual(stats['tool_regression_tests_passed'], 2)
        self.assertEqual(stats['tool_regression_tests_skipped'], 1)
        self.assertEqual(stats['tool_regression_tests_status'], 'PASS')

    def test_failed_receipt_is_rejected(self):
        self.save(dict(self.good, status='FAIL', passed=1, failures=1, exit_code=1))
        with self.assertRaises(ValueError):
            validate_receipt(self.path, self.source)

    def test_changed_source_makes_receipt_stale(self):
        self.save()
        (self.source/'example.py').write_text('VALUE = 2\n')
        with self.assertRaisesRegex(ValueError, 'source'):
            validate_receipt(self.path, self.source)

    def test_new_python_source_cannot_be_omitted_from_receipt(self):
        self.save()
        (self.source/'added.py').write_text('NEW = True\n')
        with self.assertRaisesRegex(ValueError, 'source'):
            validate_receipt(self.path, self.source)

    def test_malformed_receipts_and_inconsistent_counts_are_rejected(self):
        cases = [[], {}, dict(self.good, format='other'), dict(self.good, tests_run=True),
                 dict(self.good, tests_run=4), dict(self.good, skipped=-1),
                 dict(self.good, passed=0, skipped=3), dict(self.good, exit_code=False),
                 dict(self.good, failures=1), dict(self.good, source_unchanged=False),
                 dict(self.good, source_sha256={}), dict(self.good, source_sha256=[])]
        for receipt in cases:
            with self.subTest(receipt=receipt):
                self.save(receipt)
                with self.assertRaises(ValueError):
                    validate_receipt(self.path, self.source)

    def test_subtest_failures_are_counted_as_one_failed_case(self):
        class Synthetic(unittest.TestCase):
            def test_fails_twice(self):
                for i in range(2):
                    with self.subTest(i=i):
                        self.fail('synthetic failure')

            @unittest.skip('synthetic optional dependency')
            def test_optional(self):
                pass

            def test_passes(self):
                pass

        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, resultclass=CountedResult).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Synthetic))
        self.assertEqual(result.testsRun, 3)
        self.assertEqual(result.counts['failures'], 1)
        self.assertEqual(result.counts['passed'], 1)
        self.assertEqual(result.counts['skipped'], 1)
        self.assertEqual(len(result.failures), 2)
        self.assertFalse(result.wasSuccessful())

    def test_runner_never_overwrites_outputs_or_starts_tests_for_invalid_paths(self):
        self.path.write_text('preserve existing evidence')
        with mock.patch('run_tool_checks.unittest.TestLoader') as loader:
            with self.assertRaises(ValueError):
                run_checks(self.path)
            with self.assertRaises(ValueError):
                run_checks(self.root/'new.json', stdout_path=self.root/'new.json')
            loader.assert_not_called()
        self.assertEqual(self.path.read_text(), 'preserve existing evidence')

    def test_runner_writes_receipt_and_logs_for_safe_synthetic_suite(self):
        class Synthetic(unittest.TestCase):
            def test_pass(self):
                print('synthetic stdout only')

        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Synthetic)
        stdout, stderr = self.root/'stdout.txt', self.root/'stderr.txt'
        with mock.patch('run_tool_checks.unittest.TestLoader') as loader:
            loader.return_value.discover.return_value = suite
            with mock.patch('run_tool_checks.source_hashes', return_value=self.good['source_sha256']):
                receipt = run_checks(self.path, stdout_path=stdout, stderr_path=stderr)
        self.assertEqual(receipt['tests_run'], 1)
        self.assertEqual(receipt['passed'], 1)
        self.assertEqual(receipt['exit_code'], 0)
        self.assertIn('synthetic stdout only', stdout.read_text())
        self.assertIn('Ran 1 test', stderr.read_text())
        self.assertEqual(validate_receipt(self.path, self.source), receipt)


if __name__ == '__main__':
    unittest.main()
