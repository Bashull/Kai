"""Offline regressions using the 678-row official read snapshot of 2026-10-18.

Fake CLI responses reproduce CLI 0.4.4 transport metadata. No authentication,
vendor requests, POSTs, GIF downloads or runtime databases are used.
"""
import copy
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from kai_meshy.animation_library import AnimationLibrary, AnimationLibraryError, FRESHNESS_SECONDS
from kai_meshy.core import ForgeError, MeshyCLI


FIXTURE = Path(__file__).parent / 'fixtures/animation_library_20261018_safe.json'
NOW = datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc)


def envelope(rows):
    return {'schema_version': 'meshy.cli/v1', 'command': 'api', 'ok': True,
            'result': {'http_status': 200, 'method': 'GET', 'path': '/animations/library',
                       'api': 'v1', 'body': rows, 'saved_json': None},
            'error': None, 'warnings': []}


class FakeCLI:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def request(self, contract, action, **kwargs):
        self.calls.append((copy.deepcopy(contract), action, copy.deepcopy(kwargs)))
        return copy.deepcopy(self.response)


class AnimationLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding='utf-8'))
        cls.rows = cls.fixture['items']

    def snapshot(self, rows=None, *, response=None):
        cli = FakeCLI(response if response is not None else envelope(copy.deepcopy(self.rows if rows is None else rows)))
        with patch('kai_meshy.animation_library._utc_now', return_value=NOW):
            snapshot = AnimationLibrary.fetch(cli)
        return snapshot, cli

    def test_actual_678_rows_zero_valid_and_retired_332_rejected(self):
        snapshot, cli = self.snapshot()
        with patch('kai_meshy.animation_library._utc_now', return_value=NOW):
            self.assertEqual(snapshot.action_count, 678)
            self.assertEqual(snapshot.allowed_ids, frozenset(row['action_id'] for row in self.rows))
            self.assertEqual(snapshot.require_action(0)['name'], 'Idle')
            self.assertEqual(snapshot.require_action(92)['name'], 'Double Combo Attack')
            self.assertNotIn(332, snapshot.allowed_ids)
            with self.assertRaisesRegex(AnimationLibraryError, '^ANIMATION_ACTION_NOT_IN_CURRENT_LIBRARY$'):
                snapshot.require_action(332)
            self.assertEqual(len(snapshot.require_actions([0, 696])), 2)
        self.assertEqual(len(cli.calls), 1)

    def test_fingerprint_matches_audited_safe_cache_and_ignores_order_and_urls(self):
        first, _ = self.snapshot()
        rows = list(reversed(copy.deepcopy(self.rows)))
        for row in rows:
            row['preview_url'] = 'https://example.invalid/do-not-fetch.gif?token=private-test'
            row['unknown_vendor_field'] = {'credential': 'msy_do_not_retain'}
        second, _ = self.snapshot(rows)
        self.assertEqual(first.fingerprint_sha256, self.fixture['safe_metadata_sha256'])
        self.assertEqual(first.fingerprint_sha256, second.fingerprint_sha256)
        with patch('kai_meshy.animation_library._utc_now', return_value=NOW):
            public = json.dumps(second.as_dict(), sort_keys=True)
        for private in ('https://', 'msy_', 'private-test', 'unknown_vendor_field', 'preview_url'):
            self.assertNotIn(private, public)
        self.assertEqual(first.entries, second.entries)

    def test_only_fixed_documented_cli_get_is_issued(self):
        class RecordingCLI(MeshyCLI):
            def __init__(self, response):
                self.response = response
                self.calls = []

            def run(self, *args, **kwargs):
                self.calls.append((args, kwargs))
                return self.response

        cli = RecordingCLI(envelope(self.rows))
        AnimationLibrary.fetch(cli, timeout=12)
        self.assertEqual(cli.calls, [(('api', 'GET', '/animations/library', '--v1', '--output-schema', 'v1'), {'timeout': 12})])
        _, fake = self.snapshot()
        contract, action, kwargs = fake.calls[0]
        self.assertEqual(action, 'get')
        self.assertEqual(contract['routes'], {'get': '/openapi/v1/animations/library'})
        self.assertEqual(contract['route_methods'], {'get': 'GET'})
        self.assertEqual(kwargs, {'timeout': 30})

    def test_full_cli_and_direct_transport_metadata_are_supported(self):
        outer, _ = self.snapshot()
        direct, _ = self.snapshot(response=envelope(self.rows)['result'])
        fullpath = envelope(self.rows)
        fullpath['result']['path'] = '/openapi/v1/animations/library'
        alternative, _ = self.snapshot(response=fullpath)
        self.assertEqual(outer.entries, direct.entries)
        self.assertEqual(outer.fingerprint_sha256, alternative.fingerprint_sha256)

    def test_failed_wrong_route_method_api_or_schema_is_rejected(self):
        variants = []
        for field, value in [('http_status', 500), ('http_status', True), ('http_status', 201),
                             ('method', 'POST'), ('api', 'v2'), ('path', '/animations'),
                             ('path', '/animations/library?search=walk'), ('body', {'items': self.rows})]:
            response = envelope(self.rows)
            response['result'][field] = value
            variants.append(response)
        for field, value in [('ok', False), ('ok', None), ('command', 'balance'), ('schema_version', 'other/v1')]:
            response = envelope(self.rows); response[field] = value; variants.append(response)
        variants += [self.rows, {'result': self.rows}, {'ok': True, 'result': None}]
        for response in variants:
            with self.subTest(type(response).__name__), self.assertRaises(AnimationLibraryError):
                self.snapshot(response=response)

    def test_no_automatic_retry_and_cli_exception_details_are_sanitized(self):
        class FailingCLI:
            calls = 0

            def request(self, *args, **kwargs):
                self.calls += 1
                raise RuntimeError('msy_secret https://example.invalid/private')

        cli = FailingCLI()
        with self.assertRaisesRegex(AnimationLibraryError, '^ANIMATION_LIBRARY_FETCH_FAILED$') as caught:
            AnimationLibrary.fetch(cli)
        self.assertIsInstance(caught.exception, ForgeError)
        self.assertEqual(cli.calls, 1)
        self.assertNotIn('secret', str(caught.exception))

    def test_duplicate_ids_and_keys_rejected_but_display_names_may_repeat(self):
        first = copy.deepcopy(self.rows[0])
        second = copy.deepcopy(self.rows[1]); second['name'] = first['name']
        snapshot, _ = self.snapshot([first, second])
        self.assertEqual(snapshot.action_count, 2)
        for field in ('action_id', 'key'):
            duplicate = copy.deepcopy(second); duplicate[field] = first[field]
            with self.subTest(field), self.assertRaisesRegex(AnimationLibraryError, 'IDENTITY_DUPLICATE'):
                self.snapshot([first, duplicate])

    def test_invalid_provider_ids_and_metadata_fail_without_echo(self):
        for invalid in (None, True, False, 1.0, '0', -1, [], {}):
            row = copy.deepcopy(self.rows[0]); row['action_id'] = invalid
            with self.subTest(repr(invalid)), self.assertRaises(AnimationLibraryError):
                self.snapshot([row])
        for field in ('name', 'key', 'category', 'sub_category'):
            for invalid in (None, '', 22, 'msy_do_not_echo', 'https://example.invalid/private', 'Bearer secret', 'bad\nvalue'):
                row = copy.deepcopy(self.rows[0]); row[field] = invalid
                with self.subTest(field=field, value=repr(invalid)), self.assertRaisesRegex(AnimationLibraryError, '^ANIMATION_LIBRARY_METADATA_INVALID$'):
                    self.snapshot([row])

    def test_empty_or_excessive_row_count_rejected(self):
        for rows in ([], [self.rows[0]] * 5001):
            with self.assertRaisesRegex(AnimationLibraryError, 'LIST_INVALID'):
                self.snapshot(rows)

    def test_action_request_types_and_multi_action_bounds_are_strict(self):
        snapshot, _ = self.snapshot()
        with patch('kai_meshy.animation_library._utc_now', return_value=NOW):
            for invalid in (None, True, False, 0.0, '0', -1, [], {}):
                with self.subTest(repr(invalid)), self.assertRaises(AnimationLibraryError):
                    snapshot.require_action(invalid)
            for invalid in (None, True, [], [0, 0], [True], [0.0], list(range(11)), {'0': 0}):
                with self.subTest(repr(invalid)), self.assertRaises(AnimationLibraryError):
                    snapshot.require_actions(invalid)

    def test_receipt_freshness_uses_actual_clock_and_expires_at_300_seconds(self):
        snapshot, _ = self.snapshot()
        with patch('kai_meshy.animation_library._utc_now', return_value=NOW + timedelta(seconds=299.99)):
            receipt = snapshot.to_receipt([0, 92])
            self.assertEqual(receipt['action_ids'], [0, 92])
            self.assertEqual(receipt['source']['freshness_seconds'], 300)
            self.assertEqual(receipt['authorization'], 'NOT_GRANTED_BY_LIBRARY')
        for later in (NOW - timedelta(microseconds=1), NOW + timedelta(seconds=FRESHNESS_SECONDS), NOW + timedelta(days=1)):
            with patch('kai_meshy.animation_library._utc_now', return_value=later):
                for method in (lambda: snapshot.require_action(0), snapshot.to_receipt, snapshot.query):
                    with self.assertRaisesRegex(AnimationLibraryError, '^ANIMATION_LIBRARY_STALE_OR_FUTURE$'):
                        method()

    def test_immutable_properties_and_detached_public_metadata(self):
        snapshot, _ = self.snapshot()
        with self.assertRaises(FrozenInstanceError):
            snapshot._fingerprint = 'tampered'
        entries = snapshot.entries; entries[0]['action_id'] = 332
        source = snapshot.source; source['credits'] = 900; source['retained_fields'].clear()
        with patch('kai_meshy.animation_library._utc_now', return_value=NOW):
            row = snapshot.require_action(0); row['name'] = 'changed'
            self.assertEqual(snapshot.require_action(0)['name'], 'Idle')
            self.assertEqual(snapshot.source['credits'], 0)
            self.assertEqual(len(snapshot.source['retained_fields']), 5)

    def test_query_filters_literal_search_and_pages_local_snapshot_only(self):
        snapshot, cli = self.snapshot()
        with patch('kai_meshy.animation_library._utc_now', return_value=NOW):
            first = snapshot.query(category='Fighting', limit=7)
            self.assertEqual(first['provider_count'], 678)
            self.assertEqual(first['matched_count'], 154)
            self.assertEqual(first['next_offset'], 7)
            second = snapshot.query(category='Fighting', limit=7, offset=7)
            self.assertFalse({row['action_id'] for row in first['items']} & {row['action_id'] for row in second['items']})
            self.assertEqual(snapshot.query(search='dOuBlE_cOmBo')['items'][0]['action_id'], 92)
            self.assertEqual(snapshot.query(search='%')['matched_count'], 0)
            self.assertIsNone(snapshot.query(offset=10000)['next_offset'])
        self.assertEqual(len(cli.calls), 1)

    def test_query_and_timeout_arguments_cannot_smuggle_transport_parameters(self):
        snapshot, cli = self.snapshot()
        with patch('kai_meshy.animation_library._utc_now', return_value=NOW):
            for kwargs in ({'offset': True}, {'limit': 0}, {'limit': 101}, {'category': 'Unknown'},
                           {'search': 'https://example.invalid/private'}, {'search': 5}, {'offset': -1}):
                with self.subTest(kwargs), self.assertRaises(AnimationLibraryError):
                    snapshot.query(**kwargs)
        for timeout in (None, False, -1, 0, 61, float('nan'), float('inf'), '30'):
            with self.subTest(timeout), self.assertRaises(AnimationLibraryError):
                AnimationLibrary.fetch(cli, timeout=timeout)
        self.assertEqual(len(cli.calls), 1)

    def test_fingerprint_changes_if_semantic_metadata_changes(self):
        original, _ = self.snapshot()
        changed = copy.deepcopy(self.rows); changed[0]['category'] = 'ChangedCategory'
        revised, _ = self.snapshot(changed)
        self.assertNotEqual(original.fingerprint_sha256, revised.fingerprint_sha256)
        encoded = json.dumps(original.entries, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
        self.assertEqual(original.fingerprint_sha256, hashlib.sha256(encoded).hexdigest())


if __name__ == '__main__':
    unittest.main()
