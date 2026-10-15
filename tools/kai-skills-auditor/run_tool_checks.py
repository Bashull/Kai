"""Run only local unittest fixtures and bind their receipt to the tool sources.

No dependency installation, provider activation or historical build is performed.
Output files must be new. Optional donor tests keep their default skip behavior.
"""
import argparse
import collections
import contextlib
import datetime as dt
import io
import json
from pathlib import Path
import sys
import time
import unittest

from bundle_io import read_json, sha

SOURCE_DIR = Path(__file__).resolve().parent
COUNT_FIELDS = ('passed', 'skipped', 'failures', 'errors', 'expected_failures', 'unexpected_successes')


def source_hashes(source_dir=SOURCE_DIR):
    paths = sorted(Path(source_dir).glob('*.py'))
    if not paths or any(p.is_symlink() or not p.is_file() for p in paths):
        raise ValueError('Tool source files must be present and regular local files')
    return {p.name: sha(p.read_bytes()) for p in paths}


class CountedResult(unittest.TextTestResult):
    """Count test-case outcomes; multiple failed subtests remain one failed case."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.counts = collections.Counter()

    def startTest(self, test):
        self.outcome = 'passed'
        super().startTest(test)

    def _mark(self, outcome):
        if COUNT_FIELDS.index(outcome) > COUNT_FIELDS.index(self.outcome):
            self.outcome = outcome

    def addFailure(self, test, err):
        self._mark('failures')
        super().addFailure(test, err)

    def addError(self, test, err):
        self._mark('errors')
        super().addError(test, err)

    def addSubTest(self, test, subtest, err):
        if err is not None:
            self._mark('failures' if issubclass(err[0], test.failureException) else 'errors')
        super().addSubTest(test, subtest, err)

    def addSkip(self, test, reason):
        self._mark('skipped')
        super().addSkip(test, reason)

    def addExpectedFailure(self, test, err):
        self._mark('expected_failures')
        super().addExpectedFailure(test, err)

    def addUnexpectedSuccess(self, test):
        self._mark('unexpected_successes')
        super().addUnexpectedSuccess(test)

    def stopTest(self, test):
        self.counts[self.outcome] += 1
        super().stopTest(test)


def validate_receipt(path, source_dir=SOURCE_DIR):
    try:
        receipt = read_json(Path(path).read_bytes())
    except (OSError, ValueError) as exc:
        raise ValueError('Could not read a valid tool test receipt') from exc
    if not isinstance(receipt, dict) or receipt.get('format') != 'kai.skills.tool-tests/1':
        raise ValueError('Unsupported tool test receipt format')
    fields = ('tests_run', 'exit_code', *COUNT_FIELDS)
    if any(type(receipt.get(k)) is not int or receipt[k] < 0 for k in fields):
        raise ValueError('Tool test receipt counts/codes must be nonnegative integers')
    if receipt['tests_run'] != sum(receipt[k] for k in COUNT_FIELDS):
        raise ValueError('Tool test receipt counts are inconsistent')
    if (receipt.get('status') != 'PASS' or receipt['exit_code'] != 0
            or receipt['passed'] < 1 or receipt['failures'] or receipt['errors']
            or receipt['unexpected_successes'] or receipt.get('source_unchanged') is not True):
        raise ValueError('Tool test receipt does not establish a successful test run')
    if not isinstance(receipt.get('source_sha256'), dict) or receipt['source_sha256'] != source_hashes(source_dir):
        raise ValueError('Tool test receipt source hashes are missing, incomplete or stale')
    return receipt


def tool_test_evidence(path=None, source_dir=SOURCE_DIR):
    receipt = validate_receipt(path, source_dir) if path is not None else None
    counts = {k: receipt[k] if receipt else 0 for k in COUNT_FIELDS}
    stats = {'tool_regression_tests': receipt['tests_run'] if receipt else 0,
             'tool_regression_tests_status': 'PASS' if receipt else 'NOT_RUN',
             'tool_regression_tests_executed': sum(v for k, v in counts.items() if k != 'skipped'),
             **{'tool_regression_tests_' + k: v for k, v in counts.items()}}
    return stats, receipt


def run_checks(receipt_path, stdout_path=None, stderr_path=None):
    paths = {key: Path(path).expanduser() for key, path in
             (('receipt', receipt_path), ('stdout', stdout_path), ('stderr', stderr_path)) if path is not None}
    if len({str(p.resolve()) for p in paths.values()}) != len(paths):
        raise ValueError('Receipt/stdout/stderr paths must be distinct')
    for path in paths.values():
        if path.exists() or path.is_symlink() or path.suffix == '.py':
            raise ValueError('Test outputs must be new files, never Python sources')
    before = source_hashes()
    stdout, stderr = io.StringIO(), io.StringIO()
    start = time.monotonic()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        suite = unittest.TestLoader().discover(str(SOURCE_DIR), pattern='test_*.py')
        result = unittest.TextTestRunner(stream=stderr, verbosity=2, resultclass=CountedResult).run(suite)
    unchanged = before == source_hashes()
    counts = {k: result.counts[k] for k in COUNT_FIELDS}
    code = 0 if result.wasSuccessful() and counts['passed'] > 0 else 1
    if not unchanged:
        code = 2
    receipt = {'format': 'kai.skills.tool-tests/1', 'status': 'PASS' if code == 0 else 'FAIL',
               'date_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
               'scope': 'LOCAL_UNITTEST_DISCOVERY_ONLY_NOT_PROVIDER_RUNTIME_TESTS',
               'tests_run': result.testsRun, **counts, 'exit_code': code,
               'failure_events': len(result.failures), 'error_events': len(result.errors),
               'source_unchanged': unchanged, 'source_sha256': before,
               'elapsed_seconds': round(time.monotonic() - start, 3),
               'stdout_sha256': sha(stdout.getvalue().encode()),
               'stderr_sha256': sha(stderr.getvalue().encode()),
               'stdout_path': str(paths['stdout'].resolve()) if 'stdout' in paths else None,
               'stderr_path': str(paths['stderr'].resolve()) if 'stderr' in paths else None}
    outputs = {'receipt': json.dumps(receipt, ensure_ascii=False, indent=2) + '\n',
               'stdout': stdout.getvalue(), 'stderr': stderr.getvalue()}
    # Exclusive creation is repeated at write time to close the preflight race.
    for key in ('stdout', 'stderr', 'receipt'):
        if key in paths:
            paths[key].parent.mkdir(parents=True, exist_ok=True)
            with paths[key].open('x', encoding='utf-8') as out:
                out.write(outputs[key])
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--stdout', type=Path)
    parser.add_argument('--stderr', type=Path)
    args = parser.parse_args(argv)
    try:
        receipt = run_checks(args.receipt, args.stdout, args.stderr)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({k: receipt[k] for k in ('status', 'tests_run', *COUNT_FIELDS, 'exit_code')}, indent=2))
    return receipt['exit_code']


if __name__ == '__main__':
    sys.exit(main())
