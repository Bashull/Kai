"""Safety regressions use fake APIs and private temporary workspaces only."""
import concurrent.futures
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import struct
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from kai_meshy.core import Forge, ForgeError, MeshyCLI, digest, public_json, safe_asset_url, unwrap
from kai_meshy.assets import inspect_model
from kai_meshy.pipeline import cycle
from PIL import Image

_image = io.BytesIO()
Image.new('RGB', (16, 16), color=(70, 70, 70)).save(_image, format='PNG')
PNG = _image.getvalue() + b'\0' * 2048
PROTOTYPE = '01a15090-2515-7561-99e8-14def9e4b0ea'
BUILD = '01a15090-2515-7561-99e8-14def9e4b0eb'


class FakeCLI:
    executable = 'NOT_A_REAL_EXECUTABLE'

    def __init__(self):
        self.posts = []; self.reads = []; self.fail_post = False
        self.tasks = {
            PROTOTYPE: {'id': PROTOTYPE, 'name': 'AHU', 'status': 'SUCCEEDED', 'progress': 100,
                        'consumed_credits': 6, 'image_urls': ['https://assets.meshy.ai/preview.png?Signature=private']},
            BUILD: {'id': BUILD, 'name': 'AHU', 'status': 'SUCCEEDED', 'progress': 100,
                    'consumed_credits': 30, 'model_urls': {'glb': 'https://assets.meshy.ai/model.glb?Signature=private'}}}
        self.before_post = None

    def auth(self):
        return {'authenticated': True, 'verified': True}

    def balance(self):
        return {'balance': 3079}

    def api(self, method, path, payload=None):
        if method == 'POST':
            if self.before_post:
                self.before_post()
            self.posts.append((method, path))
            if self.fail_post:
                raise TimeoutError('lost remote reply')
            return {'result': PROTOTYPE if path.endswith('prototype') else BUILD}
        self.reads.append((method, path))
        return dict(self.tasks[path.rsplit('/', 1)[-1]])


class TestCoreSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.refs = self.base / 'refs'; self.refs.mkdir()
        self.source = self.refs / 'original.png'; self.source.write_bytes(PNG)
        self.cli = FakeCLI()
        self.forge = Forge(self.base / 'work', self.cli, reference_roots=[self.refs],
                           spending_enabled=True, spending_job_ids={'AHU'}, max_credits=40)
        self.forge.create_job('AHU', self.source, budget=40)

    def approved(self):
        self.forge.submit('AHU', 'prototype'); self.forge.refresh('AHU', 'prototype')
        preview = self.forge.root / 'jobs/AHU/preview.png'; preview.write_bytes(PNG)
        self.forge.approve('AHU', digest(preview), actor='owner')
        return preview

    def test_default_and_job_allowlist_disable_infrastructure_spend(self):
        disabled = Forge(self.base / 'disabled', self.cli, reference_roots=[self.refs])
        disabled.create_job('INFRA', self.source)
        with self.assertRaisesRegex(ForgeError, 'SPENDING_DISABLED'):
            disabled.submit('INFRA', 'prototype')
        self.forge.create_job('INFRA', self.source, 40)
        with self.assertRaisesRegex(ForgeError, 'OUTSIDE_EXPLICIT_SPENDING'):
            self.forge.submit('INFRA', 'prototype')
        self.assertEqual(self.cli.posts, [])

    def test_outside_reference_and_symlinks_never_copied(self):
        outside = self.base / 'private.png'; outside.write_bytes(PNG)
        with self.assertRaisesRegex(ForgeError, 'OUTSIDE_APPROVED_ROOTS'):
            self.forge.create_job('PRIVATE', outside, 40)
        linked = self.refs / 'linked.png'; linked.symlink_to(outside)
        with self.assertRaisesRegex(ForgeError, 'SYMLINK'):
            self.forge.create_job('LINK', linked, 40)
        linked_dir = self.refs / 'linked_dir'; linked_dir.symlink_to(self.base, target_is_directory=True)
        with self.assertRaisesRegex(ForgeError, 'SYMLINK'):
            self.forge.create_job('LINKDIR', linked_dir / 'private.png', 40)
        self.assertFalse((self.forge.root / 'jobs/PRIVATE').exists())

    def test_preflight_source_tamper_creates_no_unknown_intent(self):
        Path(self.forge.get_job('AHU')['job']['source']).write_bytes(PNG + b'tampered')
        with self.assertRaisesRegex(ForgeError, 'SOURCE_CHANGED'):
            self.forge.submit('AHU', 'prototype')
        self.assertEqual(self.forge.get_job('AHU')['stages'], [])
        self.assertEqual(self.cli.posts, [])

    def test_intent_durable_before_network_and_ambiguous_never_retried(self):
        def receipt():
            stage = self.forge.get_job('AHU')['stages'][0]
            self.assertEqual(stage['status'], 'SUBMISSION_UNKNOWN')
            self.assertEqual(len(stage['request_sha']), 64)
        self.cli.before_post = receipt; self.cli.fail_post = True
        with self.assertRaisesRegex(ForgeError, 'SUBMISSION_UNKNOWN'):
            self.forge.submit('AHU', 'prototype')
        self.cli.fail_post = False
        with self.assertRaisesRegex(ForgeError, 'STAGE_ALREADY'):
            self.forge.submit('AHU', 'prototype')
        self.assertEqual(len(self.cli.posts), 1)
        self.assertEqual(self.forge.budget_status()['committed_or_actual_credits'], 6)

    def test_two_concurrent_submitters_send_one_post(self):
        self.cli.before_post = lambda: time.sleep(0.05)
        barrier = threading.Barrier(2)
        def send():
            barrier.wait()
            try:
                self.forge.submit('AHU', 'prototype'); return 'sent'
            except ForgeError:
                return 'blocked'
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: send(), range(2)))
        self.assertCountEqual(results, ['sent', 'blocked'])
        self.assertEqual(len(self.cli.posts), 1)

    def test_approval_binds_hash_actor_and_detects_tamper(self):
        preview = self.approved()
        job = self.forge.get_job('AHU')['job']
        self.assertEqual(job['approved_actor'], 'owner')
        self.assertEqual(job['approved_preview_sha'], digest(preview))
        preview.write_bytes(b'changed visual')
        with self.assertRaisesRegex(ForgeError, 'APPROVED_PREVIEW_CHANGED'):
            self.forge.submit('AHU', 'build')
        self.assertEqual(len(self.cli.posts), 1)

    def test_response_identity_mismatch_cannot_set_success_or_credits(self):
        self.forge.submit('AHU', 'prototype')
        self.cli.tasks[PROTOTYPE]['id'] = BUILD
        with self.assertRaisesRegex(ForgeError, 'ID_OR_STATE_MISMATCH'):
            self.forge.refresh('AHU', 'prototype')
        row = self.forge.get_job('AHU')['stages'][0]
        self.assertEqual(row['status'], 'PENDING')
        self.assertIsNone(row['actual'])

    def test_real_cli_v1_transport_body_supports_historical_import(self):
        # Shape observed in a real free CLI GET, 2026-10-18; no signed URLs or
        # credentials retained. The task id/status/cost are the actual receipt.
        fixture = {'schema_version': 'v1', 'command': 'api', 'ok': True,
                   'result': {'http_status': 200, 'method': 'GET',
                              'path': '/brick-figure/v1/prototype/' + PROTOTYPE,
                              'api': 'creative-lab', 'body': {
                                  'id': PROTOTYPE, 'type': 'brick-figure', 'name': 'SANITIZED',
                                  'status': 'SUCCEEDED', 'progress': 100, 'created_at': 1792352987493,
                                  'started_at': 1792352987501, 'finished_at': 1792353009319,
                                  'expires_at': 1792612209319, 'task_error': None,
                                  'preceding_tasks': 0, 'consumed_credits': 6}, 'saved_json': None},
                   'error': None, 'warnings': []}
        with patch.object(self.cli, 'api', return_value=fixture):
            result = self.forge.import_task('AHU', 'prototype', PROTOTYPE, 6, rejected=True)
        self.assertEqual(result['stages'][0]['task_id'], PROTOTYPE)
        self.assertEqual(result['stages'][0]['actual'], 6)
        self.assertEqual(self.forge.budget_status()['committed_or_actual_credits'], 6)
        self.assertEqual(self.cli.posts, [])

    def test_cli_v1_transport_post_body_and_failure_status(self):
        fixture = {'schema_version': 'v1', 'command': 'api', 'ok': True,
                   'result': {'http_status': 200, 'method': 'POST',
                              'path': '/brick-figure/v1/prototype', 'api': 'creative-lab',
                              'body': {'result': PROTOTYPE}, 'saved_json': None},
                   'error': None, 'warnings': []}
        self.assertEqual(unwrap(fixture), PROTOTYPE)
        fixture['result']['http_status'] = 500
        with self.assertRaisesRegex(ForgeError, 'TRANSPORT_ENVELOPE'):
            unwrap(fixture)
        self.assertEqual(unwrap({'ok': True, 'result': {'balance': 3079}}), {'balance': 3079})

    def test_pending_zero_consumed_does_not_release_reservation(self):
        self.forge.submit('AHU', 'prototype')
        self.cli.tasks[PROTOTYPE].update(status='IN_PROGRESS', progress=10, consumed_credits=0)
        self.forge.refresh('AHU', 'prototype')
        self.assertEqual(self.forge.budget_status()['committed_or_actual_credits'], 6)

    def test_terminal_actual_zero_releases_known_failed_cost(self):
        self.forge.submit('AHU', 'prototype')
        self.cli.tasks[PROTOTYPE].update(status='FAILED', progress=10, consumed_credits=0)
        self.forge.refresh('AHU', 'prototype')
        self.assertEqual(self.forge.budget_status()['committed_or_actual_credits'], 0)
        with self.assertRaisesRegex(ForgeError, 'STAGE_ALREADY'):
            self.forge.submit('AHU', 'prototype')

    def test_import_historical_six_is_idempotent_and_rejection_blocks_build(self):
        for _ in range(2):
            self.forge.import_task('AHU', 'prototype', PROTOTYPE, 6, rejected=True)
        self.assertEqual(len(self.forge.get_job('AHU')['stages']), 1)
        self.assertEqual(self.forge.budget_status()['committed_or_actual_credits'], 6)
        self.assertEqual(self.cli.posts, [])
        with self.assertRaisesRegex(ForgeError, 'CANCELLED_OR_REJECTED'):
            self.forge.submit('AHU', 'build')
        with self.assertRaisesRegex(ForgeError, 'NOT_VERIFIED_REMOTELY'):
            self.forge.import_task('AHU', 'prototype', PROTOTYPE, 0)

    def test_same_remote_task_cannot_be_counted_as_two_jobs(self):
        self.forge.import_task('AHU', 'prototype', PROTOTYPE, 6)
        self.forge.create_job('OTHER', self.source, 40)
        with self.assertRaisesRegex(ForgeError, 'IMPORT_IDENTITY'):
            self.forge.import_task('OTHER', 'prototype', PROTOTYPE, 6)
        self.assertEqual(self.forge.budget_status()['committed_or_actual_credits'], 6)

    def test_unknown_reconciliation_binds_request_and_name_without_post(self):
        self.cli.fail_post = True
        with self.assertRaises(ForgeError):
            self.forge.submit('AHU', 'prototype')
        sha = self.forge.get_job('AHU')['stages'][0]['request_sha']
        with self.assertRaisesRegex(ForgeError, 'REQUEST_IDENTITY'):
            self.forge.reconcile('AHU', 'prototype', PROTOTYPE, 'wrong')
        self.cli.tasks[PROTOTYPE]['name'] = 'OTHER'
        with self.assertRaisesRegex(ForgeError, 'NOT_BOUND'):
            self.forge.reconcile('AHU', 'prototype', PROTOTYPE, sha)
        self.cli.tasks[PROTOTYPE]['name'] = self.forge.get_job('AHU')['stages'][0]['remote_name']
        result = self.forge.reconcile('AHU', 'prototype', PROTOTYPE, sha)
        self.assertEqual(result['stages'][0]['status'], 'SUCCEEDED')
        self.assertEqual(len(self.cli.posts), 1)

    def test_local_cancel_does_not_claim_remote_or_release_unknown(self):
        self.forge.submit('AHU', 'prototype')
        result = self.forge.cancel('AHU')
        self.assertFalse(result['remote_cancelled'])
        self.assertEqual(self.forge.budget_status()['committed_or_actual_credits'], 6)
        self.assertEqual(cycle(self.forge, 'AHU')['next_action'], 'LOCALLY_CANCELLED_REMOTE_UNCHANGED')

    def test_polling_stops_on_no_progress_without_regenerating(self):
        self.forge.submit('AHU', 'prototype')
        self.cli.tasks[PROTOTYPE].update(status='IN_PROGRESS', progress=5, consumed_credits=0)
        with patch('kai_meshy.core.time.sleep'):
            result = self.forge.wait('AHU', 'prototype', interval=0.05, max_stalled=2)
        self.assertEqual(result['wait_stop'], 'NO_PROGRESS_RECONCILE_SAME_TASK')
        self.assertEqual(len(self.cli.reads), 3)
        self.assertEqual(len(self.cli.posts), 1)

    def test_recovery_cycle_downloads_succeeded_preview(self):
        self.forge.import_task('AHU', 'prototype', PROTOTYPE, 6)
        with patch.object(self.forge, 'download', return_value={'sha256': 'fixture'}) as download:
            result = cycle(self.forge, 'AHU')
        download.assert_called_once_with('AHU', 'prototype', 'preview')
        self.assertEqual(result['next_action'], 'HUMAN_VISUAL_QA')
        self.assertEqual(self.cli.posts, [])

    def test_migration_uses_same_db_and_requires_new_hash_approval(self):
        root = self.base / 'legacy'; root.mkdir(); db = root / 'state.sqlite3'
        source = root / 'source.png'; source.write_bytes(PNG)
        with sqlite3.connect(db) as c:
            c.execute('CREATE TABLE jobs(id TEXT PRIMARY KEY,source TEXT,source_sha TEXT,budget INTEGER,preview_approved INTEGER,created REAL)')
            c.execute('CREATE TABLE stages(job_id TEXT,stage TEXT,status TEXT,task_id TEXT,reservation INTEGER,actual INTEGER,intent_at REAL,updated REAL,PRIMARY KEY(job_id,stage))')
            c.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?)', ('AHU', str(source), digest(source), 40, 1, 0))
            c.execute('INSERT INTO stages VALUES(?,?,?,?,?,?,?,?)', ('AHU', 'prototype', 'SUCCEEDED', PROTOTYPE, 6, 6, 0, 0))
        c.close()
        inode = db.stat().st_ino
        forge = Forge(root, self.cli, max_credits=40, spending_enabled=True, spending_job_ids={'AHU'})
        self.assertEqual(forge.db.stat().st_ino, inode)
        self.assertEqual(forge.budget_status()['committed_or_actual_credits'], 6)
        with self.assertRaisesRegex(ForgeError, 'PREVIEW_QA_NOT_APPROVED'):
            forge.submit('AHU', 'build')

    def test_global_budget_counts_historical_and_reservations(self):
        self.forge.import_task('AHU', 'prototype', PROTOTYPE, 6, rejected=True)
        small = Forge(self.forge.root, self.cli, max_credits=10, reference_roots=[self.refs],
                      spending_enabled=True, spending_job_ids={'NEXT'})
        small.create_job('NEXT', self.source, 10)
        with self.assertRaisesRegex(ForgeError, 'GLOBAL_BUDGET_EXCEEDED'):
            small.submit('NEXT', 'prototype')
        self.assertEqual(self.cli.posts, [])

    def test_default_sqlite_path_symlink_denied(self):
        root = self.base / 'linked_db'; root.mkdir()
        private = self.base / 'private.sqlite'; private.write_bytes(b'PRIVATE')
        (root / 'state.sqlite3').symlink_to(private)
        with self.assertRaisesRegex(ForgeError, 'SYMLINK'):
            Forge(root, self.cli)
        self.assertEqual(private.read_bytes(), b'PRIVATE')

    def test_corrupt_image_signature_is_not_paid_input(self):
        fake = self.refs / 'fake.png'; fake.write_bytes(b'\x89PNG\r\n\x1a\n' + b'x' * 2048)
        with self.assertRaisesRegex(ForgeError, 'IMAGE_DECODE_INVALID'):
            self.forge.create_job('FAKE', fake, 40)
        self.assertEqual(self.cli.posts, [])

    def test_cached_asset_cannot_be_trusted_without_matching_receipt(self):
        self.forge.import_task('AHU', 'prototype', PROTOTYPE, 6)
        preview = self.forge.root / 'jobs/AHU/preview.png'; preview.write_bytes(PNG)
        with self.assertRaisesRegex(ForgeError, 'CACHED_ASSET_UNREGISTERED'):
            self.forge.download('AHU', 'prototype', 'preview')
        with self.forge._db() as c:
            c.execute('INSERT INTO download_receipts VALUES(?,?,?,?,?,?,?,?)',
                      ('AHU', 'prototype', 'preview', PROTOTYPE, str(preview), digest(preview), preview.stat().st_size, 0))
        self.assertTrue(self.forge.download('AHU', 'prototype', 'preview')['cached'])
        preview.write_bytes(PNG + b'changed')
        with self.assertRaisesRegex(ForgeError, 'CACHED_ASSET_CONTENT_CHANGED'):
            self.forge.download('AHU', 'prototype', 'preview')

    def test_remote_identity_uses_full_job_id_not_truncated_prefix(self):
        a = 'X' * 60 + 'A'; b = 'X' * 60 + 'B'
        self.forge.spending_job_ids = frozenset({a, b})
        self.cli.fail_post = True
        for name in (a, b):
            self.forge.create_job(name, self.source, 40)
            with self.assertRaisesRegex(ForgeError, 'SUBMISSION_UNKNOWN'):
                self.forge.submit(name, 'prototype')
        first = self.forge.get_job(a)['stages'][0]
        second = self.forge.get_job(b)['stages'][0]
        self.assertNotEqual(first['remote_name'], second['remote_name'])
        self.cli.tasks[PROTOTYPE]['name'] = first['remote_name']
        with self.assertRaisesRegex(ForgeError, 'NOT_BOUND'):
            self.forge.reconcile(b, 'prototype', PROTOTYPE, second['request_sha'])

    def test_stale_refresh_cannot_overwrite_concurrent_terminal_success(self):
        self.forge.submit('AHU', 'prototype')
        original_api = self.cli.api
        def stale_get(method, path, payload=None):
            data = original_api(method, path, payload)
            if method == 'GET':
                with self.forge._db() as c:
                    c.execute('UPDATE stages SET status="SUCCEEDED",actual=6 WHERE job_id="AHU" AND stage="prototype"')
                data.update(status='IN_PROGRESS', progress=50, consumed_credits=0)
            return data
        self.cli.api = stale_get
        with self.assertRaisesRegex(ForgeError, 'TERMINAL_STATUS_REGRESSION'):
            self.forge.refresh('AHU', 'prototype')
        stage = self.forge.get_job('AHU')['stages'][0]
        self.assertEqual(stage['status'], 'SUCCEEDED'); self.assertEqual(stage['actual'], 6)

    def test_verified_cache_survives_vendor_retention_or_network_failure(self):
        self.forge.import_task('AHU', 'prototype', PROTOTYPE, 6)
        preview = self.forge.root / 'jobs/AHU/preview.png'; preview.write_bytes(PNG)
        with self.forge._db() as c:
            c.execute('INSERT INTO download_receipts VALUES(?,?,?,?,?,?,?,?)',
                      ('AHU', 'prototype', 'preview', PROTOTYPE, str(preview), digest(preview), preview.stat().st_size, 0))
        with patch.object(self.cli, 'api', side_effect=ForgeError('VENDOR_TASK_EXPIRED')) as api:
            self.assertTrue(self.forge.download('AHU', 'prototype', 'preview')['cached'])
            api.assert_not_called()

    def test_download_validates_atomically_then_reuses_receipt(self):
        self.forge.import_task('AHU', 'prototype', PROTOTYPE, 6)
        class Response(io.BytesIO):
            def geturl(self):
                return 'https://assets.meshy.ai/preview.png?Signature=private'
        class Opener:
            def open(self, request, timeout):
                return Response(PNG)
        with patch('kai_meshy.core.build_opener', return_value=Opener()):
            result = self.forge.download('AHU', 'prototype', 'preview')
        self.assertEqual(result['sha256'], hashlib.sha256(PNG).hexdigest())
        self.assertTrue(self.forge.download('AHU', 'prototype', 'preview')['cached'])
        self.assertEqual(list((self.forge.root / 'jobs/AHU').glob('*.part')), [])
        self.assertEqual(self.cli.posts, [])

    def test_failed_download_never_marks_asset_or_regenerates_paid_task(self):
        self.forge.import_task('AHU', 'prototype', PROTOTYPE, 6)
        class Response(io.BytesIO):
            def geturl(self):
                return 'https://assets.meshy.ai/preview.png'
        class Opener:
            def open(self, request, timeout):
                return Response(b'not an image')
        with patch('kai_meshy.core.build_opener', return_value=Opener()):
            with self.assertRaisesRegex(ForgeError, 'IMAGE_DECODE_INVALID'):
                self.forge.download('AHU', 'prototype', 'preview')
        self.assertFalse((self.forge.root / 'jobs/AHU/preview.png').exists())
        self.assertEqual(list((self.forge.root / 'jobs/AHU').glob('*.part')), [])
        self.assertEqual(self.cli.posts, [])
        self.assertEqual(self.forge.budget_status()['committed_or_actual_credits'], 6)

    def test_android_interrupted_copy_remains_unregistered_and_preserved(self):
        self.forge.import_task('AHU', 'prototype', PROTOTYPE, 6)
        class Response(io.BytesIO):
            def geturl(self):
                return 'https://assets.meshy.ai/preview.png'
        class Opener:
            def open(self, request, timeout):
                return Response(PNG)
        def interrupted(source, out, length):
            out.write(b'partial'); raise OSError('disk interrupted')
        with patch('kai_meshy.core.build_opener', return_value=Opener()), patch('kai_meshy.core.shutil.copyfileobj', side_effect=interrupted):
            with self.assertRaises(OSError):
                self.forge.download('AHU', 'prototype', 'preview')
        preview = self.forge.root / 'jobs/AHU/preview.png'
        self.assertEqual(preview.read_bytes(), b'partial')
        with self.assertRaisesRegex(ForgeError, 'CACHED_ASSET_UNREGISTERED'):
            self.forge.download('AHU', 'prototype', 'preview')
        self.assertEqual(preview.read_bytes(), b'partial')
        self.assertEqual(self.cli.posts, [])

    def test_android_model_download_validates_temp_with_explicit_format(self):
        self.forge.import_task('AHU', 'build', BUILD, 30)
        model = glb_bytes({'asset': {'version': '2.0'}, 'meshes': [{}]})
        class Response(io.BytesIO):
            def geturl(self):
                return 'https://assets.meshy.ai/model.glb'
        class Opener:
            def open(self, request, timeout):
                return Response(model)
        with patch('kai_meshy.core.build_opener', return_value=Opener()):
            result = self.forge.download('AHU', 'build', 'glb')
        self.assertEqual(result['sha256'], hashlib.sha256(model).hexdigest())
        self.assertTrue(self.forge.download('AHU', 'build', 'glb')['cached'])

    def test_public_results_do_not_leak_url_or_token_literals(self):
        value = {'url': 'https://private', 'message': 'Bearer secret', 'nested': ['https://asset?Signature=secret'], 'consumed_credits': 6}
        self.assertEqual(public_json(value), {'message': '[REDACTED]', 'nested': ['[REDACTED]'], 'consumed_credits': 6})
        for bad in ('http://assets.meshy.ai/x', 'https://assets.meshy.ai.attacker/x', 'https://u@assets.meshy.ai/x', 'file:///etc/passwd'):
            self.assertFalse(safe_asset_url(bad))


def glb_bytes(meta, binary=b''):
    data = json.dumps(meta).encode(); data += b' ' * (-len(data) % 4)
    chunks = struct.pack('<II', len(data), 0x4E4F534A) + data
    if binary:
        binary += b'\0' * (-len(binary) % 4)
        chunks += struct.pack('<II', len(binary), 0x004E4942) + binary
    return struct.pack('<4sII', b'glTF', 2, 12 + len(chunks)) + chunks


class TestStructureBoundaries(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_glb_valid_structure_preserves_scope(self):
        p = self.root / 'model.glb'; p.write_bytes(glb_bytes({'asset': {'version': '2.0'}, 'meshes': [{}]}))
        result = inspect_model(p)
        self.assertEqual(result['meshes'], 1)
        self.assertFalse(result['mesh_qa_verified']); self.assertFalse(result['printability_verified'])

    def test_glb_chunk_and_buffer_bounds_rejected(self):
        p = self.root / 'bad.glb'
        p.write_bytes(glb_bytes({'asset': {'version': '2.0'}, 'buffers': [{'byteLength': 100}]}, b'1234'))
        with self.assertRaisesRegex(ForgeError, 'BUFFER_SIZE_MISMATCH'):
            inspect_model(p)
        raw = bytearray(glb_bytes({'asset': {'version': '2.0'}})); struct.pack_into('<I', raw, 12, 4000); p.write_bytes(raw)
        with self.assertRaisesRegex(ForgeError, 'CHUNK_BOUNDS'):
            inspect_model(p)

    def test_truncated_fbx_and_obj_invalid_indices_rejected(self):
        p = self.root / 'bad.fbx'; p.write_bytes(b'Kaydara FBX Binary')
        with self.assertRaisesRegex(ForgeError, 'TRUNCATED'):
            inspect_model(p)
        p = self.root / 'bad.obj'; p.write_text('v 0 0 0\nf 1 2 3\n')
        with self.assertRaisesRegex(ForgeError, 'INDEX_OUT_OF_BOUNDS'):
            inspect_model(p)


class TestCLIProcessBoundary(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_node_shebang_bypasses_android_missing_usr_bin_env(self):
        entry = self.root / 'meshy.js'; entry.write_text('#!/usr/bin/env node\n')
        node = self.root / 'node'; node.write_bytes(b'FAKE_NODE_NOT_EXECUTED')
        cli = MeshyCLI(entry)
        process = type('Process', (), {'returncode': 0, 'stdout': '{"balance":3079}'})()
        with patch.dict(os.environ, {'KAI_MESHY_NODE': str(node)}, clear=True), \
                patch('kai_meshy.core.subprocess.run', return_value=process) as run:
            self.assertEqual(cli.run('balance'), {'balance': 3079})
        self.assertEqual(run.call_args.args[0][:2], [str(node), str(entry)])

    def test_missing_cli_error_is_machine_code_without_private_exception_text(self):
        cli = MeshyCLI(self.root / 'missing')
        with self.assertRaises(ForgeError) as error:
            cli.run('balance')
        self.assertEqual(str(error.exception), 'CLI_UNAVAILABLE_OR_TIMED_OUT:FILENOTFOUNDERROR')
        self.assertNotIn(str(self.root), str(error.exception))

    def test_sdk_preserves_cli_machine_error_without_private_path(self):
        from kai_meshy.sdk_server import _call
        cli = MeshyCLI(self.root / 'missing')
        result = _call(cli.balance).structured_content
        self.assertFalse(result['ok'])
        self.assertEqual(result['error'], 'CLI_UNAVAILABLE_OR_TIMED_OUT:FILENOTFOUNDERROR')
        self.assertNotIn(str(self.root), json.dumps(result))


if __name__ == '__main__':
    unittest.main()
