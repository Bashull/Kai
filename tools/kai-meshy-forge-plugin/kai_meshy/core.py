"""Governed local Meshy adapter with migrations of the v0.1 staging database.

Lineage: user-supplied KAI_MESHY_FORGE_MCP_v0_1_STAGING.zip, SHA256
5c2b34bd4f8d5e78ab0e5dc3d0f1e092d59feca96b7c5b95662ec08500d9708d.
User-authorized staging integration; donor license metadata is UNSPECIFIED.
No embedded credentials.
The CLI owns authentication; this module never opens its credential store.
"""
import base64
from contextlib import contextmanager
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time
import warnings
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler

PRICES = {'prototype': 6, 'build': 30}
STAGES = tuple(PRICES)
STATUSES = {'PENDING', 'IN_PROGRESS', 'SUCCEEDED', 'FAILED', 'CANCELED'}
ALLOWED_ASSET_HOSTS = {'assets.meshy.ai'}
TASK_ID = re.compile(r'^[a-zA-Z0-9-]{8,100}$')
JOB_ID = re.compile(r'^[a-zA-Z0-9_-]{1,70}$')
COMMITTED_SQL = 'CASE WHEN status IN ("SUCCEEDED","FAILED","CANCELED") AND actual IS NOT NULL THEN actual ELSE max(reservation,coalesce(actual,0)) END'


class ForgeError(RuntimeError):
    pass


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def public_json(obj):
    if isinstance(obj, list):
        return [public_json(x) for x in obj]
    if isinstance(obj, dict):
        private = ('url', 'token', 'key', 'credential', 'authorization', 'image_data', 'payload', 'base64')
        return {k: public_json(v) for k, v in obj.items() if not any(t in k.lower() for t in private)}
    if isinstance(obj, str):
        if re.search(r'(msy_|Bearer |https?://|data:image/|[?&](?:Expires|Signature)=)', obj, re.I):
            return '[REDACTED]'
        return obj[:2000]
    return obj


def unwrap(obj):
    if not isinstance(obj, dict) or obj.get('ok') is False:
        raise ForgeError('INVALID_OR_FAILED_API_RESPONSE')
    value = obj.get('result', obj)
    # Official CLI 0.4.4 `api --output-schema v1` returns transport metadata
    # around the upstream JSON: result.{http_status,method,path,api,body,saved_json}.
    # The REST task belongs to body, while the dedicated balance command's
    # result is already its upstream JSON. Never loosen task identity validation.
    if isinstance(value, dict) and 'http_status' in value and 'body' in value:
        status = value['http_status']
        if (isinstance(status, bool) or not isinstance(status, int) or not 200 <= status < 300 or
                value.get('method') not in {'GET', 'POST', 'DELETE', 'PATCH', 'PUT'} or
                not isinstance(value.get('path'), str) or not value['path'].startswith('/')):
            raise ForgeError('CLI_TRANSPORT_ENVELOPE_INVALID_OR_FAILED')
        value = value['body']
    if isinstance(value, dict) and value.get('ok') is False:
        raise ForgeError('INVALID_OR_FAILED_API_RESPONSE')
    if isinstance(value, dict) and 'result' in value and 'id' not in value and 'status' not in value and len(value) < 5 and isinstance(value['result'], (dict, str)):
        value = value['result']
    return value


class MeshyCLI:
    def __init__(self, executable=None, timeout=180):
        self.executable = str(Path(executable).expanduser()) if executable else os.environ.get('KAI_MESHY_CLI', 'meshy')
        self.timeout = timeout

    def run(self, *args, timeout=None):
        try:
            p = subprocess.run([self.executable, *args, '--format', 'json', '--no-update-check'],
                               capture_output=True, text=True, timeout=timeout or self.timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ForgeError('CLI_UNAVAILABLE_OR_TIMED_OUT:' + type(exc).__name__) from None
        if p.returncode:
            raise ForgeError('CLI_ERROR_EXIT_' + str(p.returncode))
        try:
            return json.loads(p.stdout)
        except json.JSONDecodeError:
            raise ForgeError('CLI_INVALID_JSON') from None

    def balance(self):
        value = unwrap(self.run('balance', '--output-schema', 'v1'))
        if not isinstance(value, dict):
            raise ForgeError('BALANCE_RESPONSE_INVALID')
        return value

    def auth(self):
        value = self.run('auth', 'status')
        return {k: value.get(k) is True for k in ('authenticated', 'verified')}

    def api(self, method, path, payload=None):
        args = ['api', method, path, '--creative-lab', '--output-schema', 'v1']
        if payload is None:
            return self.run(*args)
        fd, name = tempfile.mkstemp(prefix='kai_meshy_', suffix='.json')
        try:
            with os.fdopen(fd, 'w', encoding='utf8') as f:
                json.dump(payload, f)
            return self.run(*args, '--data', '@' + name)
        finally:
            Path(name).unlink(missing_ok=True)


def safe_asset_url(url):
    try:
        p = urlparse(url)
        return p.scheme == 'https' and p.hostname in ALLOWED_ASSET_HOSTS and p.port in (None, 443) and not p.username and not p.password
    except (TypeError, ValueError):
        return False


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not safe_asset_url(newurl):
            raise ForgeError('ASSET_REDIRECT_NOT_ALLOWED')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _no_symlink(path):
    path = Path(os.path.abspath(Path(path).expanduser()))
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise ForgeError('SYMLINK_NOT_ALLOWED')
    return path


def _credits(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ForgeError('CREDIT_VALUE_INVALID')
    return value


class Forge:
    def __init__(self, root, cli=None, max_credits=500, reference_roots=None,
                 spending_enabled=False, db_path=None, spending_job_ids=None):
        self.root = _no_symlink(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = _no_symlink(db_path if db_path else self.root / 'state.sqlite3').resolve()
        if not self.db.parent.is_dir():
            raise ForgeError('EXPLICIT_LEDGER_PARENT_MISSING')
        self.cli = cli or MeshyCLI()
        if isinstance(max_credits, bool) or not isinstance(max_credits, int) or not 1 <= max_credits <= 500:
            raise ForgeError('MAXIMUM_AUTHORIZED_BUDGET_IS_500')
        self.max_credits = max_credits
        self.spending_enabled = spending_enabled is True
        self.spending_job_ids = frozenset(spending_job_ids or ())
        if any(not isinstance(job, str) or not JOB_ID.fullmatch(job) for job in self.spending_job_ids):
            raise ForgeError('INVALID_SPENDING_JOB_ALLOWLIST')
        roots = reference_roots if reference_roots is not None else [self.root]
        self.reference_roots = tuple(_no_symlink(p).resolve(strict=True) for p in roots)
        if not self.reference_roots or not all(p.is_dir() for p in self.reference_roots):
            raise ForgeError('REFERENCE_ROOTS_MUST_BE_EXPLICIT_DIRECTORIES')
        self._init()

    @contextmanager
    def _db(self):
        con = sqlite3.connect(self.db, timeout=20)
        con.row_factory = sqlite3.Row
        try:
            with con:
                yield con
        finally:
            con.close()

    def _init(self):
        # Additive migration of the original jobs/stages tables, never another ledger.
        with self._db() as con:
            con.execute('PRAGMA journal_mode=WAL')
            con.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, source TEXT NOT NULL, source_sha TEXT NOT NULL, budget INTEGER NOT NULL, preview_approved INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL)')
            con.execute('CREATE TABLE IF NOT EXISTS stages (job_id TEXT NOT NULL, stage TEXT NOT NULL, status TEXT NOT NULL, task_id TEXT, reservation INTEGER NOT NULL, actual INTEGER, intent_at REAL NOT NULL, updated REAL NOT NULL, PRIMARY KEY(job_id,stage))')
            additions = {'jobs': {'approved_preview_sha': 'TEXT', 'approved_actor': 'TEXT', 'approved_at': 'REAL',
                                  'local_cancelled': 'INTEGER NOT NULL DEFAULT 0', 'cancel_reason': 'TEXT', 'rejected': 'INTEGER NOT NULL DEFAULT 0'},
                         'stages': {'request_sha': 'TEXT', 'source_sha': 'TEXT', 'imported': 'INTEGER NOT NULL DEFAULT 0', 'remote_name': 'TEXT'}}
            for table, cols in additions.items():
                existing = {r['name'] for r in con.execute('PRAGMA table_info(' + table + ')')}
                for name, definition in cols.items():
                    if name not in existing:
                        con.execute('ALTER TABLE ' + table + ' ADD COLUMN ' + name + ' ' + definition)
            con.execute('CREATE TABLE IF NOT EXISTS audit_events (id INTEGER PRIMARY KEY, job_id TEXT, event TEXT NOT NULL, detail TEXT NOT NULL, created REAL NOT NULL)')
            con.execute('CREATE TABLE IF NOT EXISTS download_receipts (job_id TEXT NOT NULL,stage TEXT NOT NULL,format TEXT NOT NULL,task_id TEXT NOT NULL,path TEXT NOT NULL,sha256 TEXT NOT NULL,bytes INTEGER NOT NULL,created REAL NOT NULL,PRIMARY KEY(job_id,stage,format))')
            try:
                con.execute('CREATE UNIQUE INDEX IF NOT EXISTS stages_task_identity ON stages(stage,task_id) WHERE task_id IS NOT NULL')
            except sqlite3.IntegrityError:
                raise ForgeError('EXISTING_DUPLICATE_TASK_IDENTITIES_REQUIRE_RECONCILIATION') from None
        os.chmod(self.db, 0o600)

    @staticmethod
    def _event(c, job_id, event, detail):
        c.execute('INSERT INTO audit_events(job_id,event,detail,created) VALUES(?,?,?,?)',
                  (job_id, event, json.dumps(public_json(detail), sort_keys=True), time.time()))

    def _workspace_path(self, path, strict=True):
        p = _no_symlink(path).resolve(strict=strict)
        if not p.is_relative_to(self.root):
            raise ForgeError('PATH_OUTSIDE_WORKSPACE')
        return p

    def _source_bytes(self, source):
        src = _no_symlink(source).resolve(strict=True)
        if not any(src.is_relative_to(root) for root in self.reference_roots):
            raise ForgeError('REFERENCE_OUTSIDE_APPROVED_ROOTS')
        if not src.is_file() or src.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp'):
            raise ForgeError('REFERENCE_MUST_BE_LOCAL_IMAGE')
        if not 1024 <= src.stat().st_size <= 20 * 1024 * 1024:
            raise ForgeError('IMAGE_SIZE_OUT_OF_RANGE')
        fd = os.open(src, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(fd, 'rb') as f:
            data = f.read(20 * 1024 * 1024 + 1)
        if len(data) > 20 * 1024 * 1024:
            raise ForgeError('IMAGE_SIZE_OUT_OF_RANGE')
        if not (data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff') or
                (data.startswith(b'RIFF') and data[8:12] == b'WEBP')):
            raise ForgeError('IMAGE_SIGNATURE_INVALID')
        actual_format = self._decode_image(io.BytesIO(data))
        expected_format = {'.png': 'PNG', '.jpg': 'JPEG', '.jpeg': 'JPEG', '.webp': 'WEBP'}[src.suffix.lower()]
        if actual_format != expected_format:
            raise ForgeError('IMAGE_FORMAT_EXTENSION_MISMATCH')
        return src, data

    @staticmethod
    def _decode_image(source):
        try:
            from PIL import Image
        except ImportError:
            raise ForgeError('IMAGE_DECODER_REQUIRED_NO_PAID_FALLBACK') from None
        try:
            image_bytes = source.getvalue() if isinstance(source, io.BytesIO) else None
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(image_bytes) if image_bytes is not None else source) as image:
                    if image.format not in {'PNG', 'JPEG', 'WEBP'} or not 0 < image.width * image.height <= 40_000_000:
                        raise ForgeError('IMAGE_DIMENSIONS_OR_CODEC_NOT_ALLOWED')
                    image_format = image.format
                    image.verify()
                with Image.open(io.BytesIO(image_bytes) if image_bytes is not None else source) as image:
                    image.load()
            return image_format
        except ForgeError:
            raise
        except (OSError, ValueError, SyntaxError, EOFError, Image.DecompressionBombError, Image.DecompressionBombWarning):
            raise ForgeError('IMAGE_DECODE_INVALID') from None

    def get_job(self, job_id):
        with self._db() as c:
            j = c.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
            rows = c.execute('SELECT * FROM stages WHERE job_id=? ORDER BY intent_at', (job_id,)).fetchall()
        if not j:
            raise ForgeError('JOB_NOT_FOUND')
        return {'job': dict(j), 'stages': [dict(r) for r in rows]}

    def list_jobs(self):
        with self._db() as c:
            return [dict(r) for r in c.execute('SELECT id,budget,preview_approved,local_cancelled,rejected FROM jobs ORDER BY created')]

    def budget_status(self):
        with self._db() as c:
            charged = c.execute('SELECT coalesce(sum(' + COMMITTED_SQL + '),0) FROM stages').fetchone()[0]
            unknown = c.execute('SELECT count(*) FROM stages WHERE status="SUBMISSION_UNKNOWN"').fetchone()[0]
        return {'max_credits': self.max_credits, 'committed_or_actual_credits': charged,
                'remaining_authorized_credits': max(0, self.max_credits - charged),
                'uncertain_submissions': unknown, 'spending_enabled': self.spending_enabled,
                'spending_job_ids': sorted(self.spending_job_ids)}

    def create_job(self, job_id, source, budget=500):
        if not isinstance(job_id, str) or not JOB_ID.fullmatch(job_id):
            raise ForgeError('INVALID_JOB_ID')
        if isinstance(budget, bool) or not isinstance(budget, int) or not 1 <= budget <= self.max_credits:
            raise ForgeError('JOB_BUDGET_OUTSIDE_AUTHORIZED_LIMIT')
        src, data = self._source_bytes(source)
        source_sha = hashlib.sha256(data).hexdigest()
        target_dir = self._workspace_path(self.root / 'jobs' / job_id, strict=False)
        target_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        target = self._workspace_path(target_dir / ('source' + src.suffix.lower()), strict=False)
        with self._db() as c:
            c.execute('BEGIN IMMEDIATE')
            old = c.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
            if old and (old['source_sha'] != source_sha or old['budget'] != budget):
                raise ForgeError('EXISTING_JOB_CONFLICT')
            if target.exists():
                if digest(target) != source_sha:
                    raise ForgeError('IMMUTABLE_SOURCE_CONFLICT')
            else:
                fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'wb') as f:
                    f.write(data); f.flush(); os.fsync(f.fileno())
            if not old:
                c.execute('INSERT INTO jobs(id,source,source_sha,budget,created) VALUES(?,?,?,?,?)',
                          (job_id, str(target), source_sha, budget, time.time()))
                self._event(c, job_id, 'JOB_CREATED', {'source_sha': source_sha, 'budget': budget})
        return self.get_job(job_id)

    def _job_gate(self, c, job_id, stage):
        job = c.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
        if not job:
            raise ForgeError('JOB_NOT_FOUND')
        if job['local_cancelled'] or job['rejected']:
            raise ForgeError('JOB_CANCELLED_OR_REJECTED')
        if c.execute('SELECT 1 FROM stages WHERE job_id=? AND stage=?', (job_id, stage)).fetchone():
            raise ForgeError('STAGE_ALREADY_REGISTERED_NO_DUPLICATE_POST')
        if stage == 'build':
            p = c.execute('SELECT * FROM stages WHERE job_id=? AND stage="prototype"', (job_id,)).fetchone()
            if not p or p['status'] != 'SUCCEEDED' or not p['task_id']:
                raise ForgeError('PROTOTYPE_NOT_SUCCEEDED')
            if not job['preview_approved'] or not job['approved_preview_sha'] or not job['approved_actor']:
                raise ForgeError('PREVIEW_QA_NOT_APPROVED')
            preview = self._workspace_path(self.root / 'jobs' / job_id / 'preview.png')
            if digest(preview) != job['approved_preview_sha']:
                raise ForgeError('APPROVED_PREVIEW_CHANGED')
        cost = PRICES[stage]
        job_cost = c.execute('SELECT coalesce(sum(' + COMMITTED_SQL + '),0) FROM stages WHERE job_id=?', (job_id,)).fetchone()[0]
        total = c.execute('SELECT coalesce(sum(' + COMMITTED_SQL + '),0) FROM stages').fetchone()[0]
        if job_cost + cost > job['budget']:
            raise ForgeError('JOB_BUDGET_EXCEEDED')
        if total + cost > self.max_credits:
            raise ForgeError('GLOBAL_BUDGET_EXCEEDED')
        return job

    def submit(self, job_id, stage):
        if stage not in STAGES:
            raise ForgeError('INVALID_STAGE')
        if not self.spending_enabled:
            raise ForgeError('SPENDING_DISABLED_REQUIRES_EXPLICIT_CONFIGURATION')
        if job_id not in self.spending_job_ids:
            raise ForgeError('JOB_OUTSIDE_EXPLICIT_SPENDING_AUTHORIZATION')
        # All deterministic preflight happens before an intent or charge exists.
        with self._db() as c:
            job = self._job_gate(c, job_id, stage)
            source = self._workspace_path(job['source'])
            source_data = source.read_bytes()
            if hashlib.sha256(source_data).hexdigest() != job['source_sha']:
                raise ForgeError('SOURCE_CHANGED')
            self._decode_image(io.BytesIO(source_data))
            parent = c.execute('SELECT task_id FROM stages WHERE job_id=? AND stage="prototype"', (job_id,)).fetchone()
        if stage == 'prototype':
            mime = {'.png': 'png', '.jpg': 'jpeg', '.jpeg': 'jpeg', '.webp': 'webp'}[source.suffix.lower()]
            payload = {'image_url': 'data:image/' + mime + ';base64,' + base64.b64encode(source_data).decode('ascii')}
        else:
            payload = {'input_task_id': parent['task_id']}
        identity = {'job_id': job_id, 'stage': stage, 'source_sha': job['source_sha'],
                    'parent_task_id': parent['task_id'] if stage == 'build' else None, 'parameters': payload}
        fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        remote_name = 'KAI-' + fingerprint[:48]
        payload['name'] = remote_name
        request_sha = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        auth = self.cli.auth()
        if auth.get('authenticated') is not True or auth.get('verified') is not True:
            raise ForgeError('ACCOUNT_NOT_VERIFIED')
        available = _credits(self.cli.balance().get('balance'))
        if available < PRICES[stage]:
            raise ForgeError('INSUFFICIENT_API_BALANCE')
        with self._db() as c:
            c.execute('BEGIN IMMEDIATE')
            self._job_gate(c, job_id, stage)
            if digest(source) != job['source_sha']:
                raise ForgeError('SOURCE_CHANGED')
            c.execute('INSERT INTO stages(job_id,stage,status,reservation,intent_at,updated,request_sha,source_sha,remote_name) VALUES(?,?,?,?,?,?,?,?,?)',
                      (job_id, stage, 'SUBMISSION_UNKNOWN', PRICES[stage], time.time(), time.time(), request_sha, job['source_sha'], remote_name))
            self._event(c, job_id, 'SUBMISSION_INTENT', {'stage': stage, 'request_sha': request_sha, 'reserved': PRICES[stage]})
        try:
            value = unwrap(self.cli.api('POST', '/brick-figure/v1/' + stage, payload))
            task_id = value if isinstance(value, str) else value.get('id') if isinstance(value, dict) else None
            if not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id):
                raise ForgeError('INVALID_POST_TASK_ID')
            with self._db() as c:
                c.execute('UPDATE stages SET task_id=?,status="PENDING",updated=? WHERE job_id=? AND stage=?',
                          (task_id, time.time(), job_id, stage))
                self._event(c, job_id, 'SUBMISSION_CONFIRMED', {'stage': stage, 'task_id': task_id})
        except Exception:
            raise ForgeError('SUBMISSION_UNKNOWN_DO_NOT_RETRY_RECONCILE_HISTORY') from None
        return {'job_id': job_id, 'stage': stage, 'task_id': task_id, 'status': 'PENDING',
                'reserved_credits': PRICES[stage], 'request_sha256': request_sha}

    def _task(self, stage, task_id):
        if stage not in STAGES or not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id):
            raise ForgeError('INVALID_REMOTE_TASK_IDENTITY')
        data = unwrap(self.cli.api('GET', '/brick-figure/v1/' + stage + '/' + task_id))
        if not isinstance(data, dict) or data.get('id') != task_id or data.get('status') not in STATUSES:
            raise ForgeError('REMOTE_TASK_ID_OR_STATE_MISMATCH')
        if data.get('consumed_credits') is not None:
            _credits(data['consumed_credits'])
        return data

    def refresh(self, job_id, stage):
        with self._db() as c:
            row = c.execute('SELECT * FROM stages WHERE job_id=? AND stage=?', (job_id, stage)).fetchone()
        if not row or not row['task_id']:
            raise ForgeError('NO_CONFIRMED_TASK_RECONCILE_UNKNOWN')
        data = self._task(stage, row['task_id'])
        with self._db() as c:
            c.execute('BEGIN IMMEDIATE')
            latest = c.execute('SELECT * FROM stages WHERE job_id=? AND stage=?', (job_id, stage)).fetchone()
            if not latest or latest['task_id'] != row['task_id']:
                raise ForgeError('CONCURRENT_TASK_IDENTITY_CHANGED')
            if latest['status'] in {'SUCCEEDED', 'FAILED', 'CANCELED'}:
                if data['status'] != latest['status']:
                    raise ForgeError('TERMINAL_STATUS_REGRESSION_REQUIRES_RECONCILIATION')
                if latest['actual'] is not None and data.get('consumed_credits') is not None and latest['actual'] != data['consumed_credits']:
                    raise ForgeError('TERMINAL_COST_CHANGED_REQUIRES_RECONCILIATION')
            c.execute('UPDATE stages SET status=?,actual=coalesce(?,actual),updated=? WHERE job_id=? AND stage=?',
                      (data['status'], data.get('consumed_credits'), time.time(), job_id, stage))
            self._event(c, job_id, 'TASK_OBSERVED', {'stage': stage, 'task_id': row['task_id'],
                                                  'status': data['status'], 'consumed_credits': data.get('consumed_credits')})
        return {'task_id': row['task_id'], 'stage': stage, 'status': data['status'],
                'progress': data.get('progress'), 'consumed_credits': data.get('consumed_credits')}

    def wait(self, job_id, stage, timeout=1200, interval=5, max_attempts=120, max_stalled=30):
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 3600:
            raise ForgeError('INVALID_POLL_TIMEOUT')
        if not 0.05 <= interval <= 60 or not 1 <= max_attempts <= 1000 or not 1 <= max_stalled <= 1000:
            raise ForgeError('INVALID_POLL_LIMITS')
        end = time.monotonic() + timeout
        previous = None; stalled = 0
        for attempt in range(max_attempts):
            with self._db() as c:
                job = c.execute('SELECT local_cancelled FROM jobs WHERE id=?', (job_id,)).fetchone()
            if job and job['local_cancelled']:
                return {'status': 'LOCAL_WAIT_CANCELLED_REMOTE_UNCHANGED', 'job_id': job_id, 'stage': stage}
            if time.monotonic() >= end:
                break
            result = self.refresh(job_id, stage)
            if result['status'] in {'SUCCEEDED', 'FAILED', 'CANCELED'}:
                return result
            signature = (result['status'], result.get('progress'))
            stalled = stalled + 1 if signature == previous else 0
            previous = signature
            if stalled >= max_stalled:
                return {**result, 'wait_stop': 'NO_PROGRESS_RECONCILE_SAME_TASK', 'attempts': attempt + 1}
            time.sleep(min(interval, max(0, end - time.monotonic())))
        return {'status': 'WAIT_LIMIT_TASK_MAY_STILL_RUN', 'job_id': job_id, 'stage': stage}

    def approve(self, job_id, sha256, actor='user'):
        if not isinstance(actor, str) or not re.fullmatch(r'[\w .@-]{1,100}', actor):
            raise ForgeError('APPROVAL_ACTOR_REQUIRED')
        with self._db() as c:
            c.execute('BEGIN IMMEDIATE')
            job = c.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
            p = c.execute('SELECT status FROM stages WHERE job_id=? AND stage="prototype"', (job_id,)).fetchone()
            if not job or job['local_cancelled'] or job['rejected'] or not p or p['status'] != 'SUCCEEDED':
                raise ForgeError('JOB_OR_PROTOTYPE_NOT_APPROVABLE')
            preview = self._workspace_path(self.root / 'jobs' / job_id / 'preview.png')
            if not isinstance(sha256, str) or digest(preview) != sha256:
                raise ForgeError('VISUAL_APPROVAL_SHA_MISMATCH')
            c.execute('UPDATE jobs SET preview_approved=1,approved_preview_sha=?,approved_actor=?,approved_at=? WHERE id=?',
                      (sha256, actor, time.time(), job_id))
            self._event(c, job_id, 'VISUAL_APPROVAL', {'sha256': sha256, 'actor': actor})
        return {'job_id': job_id, 'preview_approved': True, 'sha256': sha256, 'actor': actor}

    def cancel(self, job_id, reason='user request'):
        if not isinstance(reason, str) or not 1 <= len(reason) <= 500:
            raise ForgeError('CANCEL_REASON_REQUIRED')
        with self._db() as c:
            if not c.execute('SELECT 1 FROM jobs WHERE id=?', (job_id,)).fetchone():
                raise ForgeError('JOB_NOT_FOUND')
            c.execute('UPDATE jobs SET local_cancelled=1,cancel_reason=? WHERE id=?', (reason, job_id))
            self._event(c, job_id, 'LOCAL_CANCEL', {'reason': reason, 'remote_cancelled': False})
        return {'job_id': job_id, 'local_cancelled': True, 'remote_cancelled': False,
                'reservations_preserved': True}

    def import_task(self, job_id, stage, task_id, actual_credits, status='SUCCEEDED', rejected=False):
        if stage not in STAGES or status not in STATUSES or not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id):
            raise ForgeError('INVALID_IMPORTED_TASK')
        actual = _credits(actual_credits)
        remote = self._task(stage, task_id)
        if remote['status'] != status or remote.get('consumed_credits') != actual:
            raise ForgeError('IMPORTED_COST_OR_STATUS_NOT_VERIFIED_REMOTELY')
        with self._db() as c:
            c.execute('BEGIN IMMEDIATE')
            job = c.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
            if not job:
                raise ForgeError('CREATE_LOCAL_JOB_BEFORE_IMPORT')
            old = c.execute('SELECT * FROM stages WHERE (stage=? AND task_id=?) OR (job_id=? AND stage=?)',
                            (stage, task_id, job_id, stage)).fetchone()
            if old:
                if old['job_id'] != job_id or old['stage'] != stage or old['task_id'] != task_id or old['actual'] != actual or old['status'] != status:
                    raise ForgeError('IMPORT_IDENTITY_OR_COST_CONFLICT')
            else:
                c.execute('INSERT INTO stages(job_id,stage,status,task_id,reservation,actual,intent_at,updated,source_sha,imported) VALUES(?,?,?,?,?,?,?,?,?,1)',
                          (job_id, stage, status, task_id, max(actual, PRICES[stage]), actual, time.time(), time.time(), job['source_sha']))
                self._event(c, job_id, 'HISTORICAL_TASK_IMPORTED', {'stage': stage, 'task_id': task_id, 'actual': actual})
            if rejected:
                c.execute('UPDATE jobs SET rejected=1,preview_approved=0 WHERE id=?', (job_id,))
        return self.get_job(job_id)

    def reconcile(self, job_id, stage, task_id, request_sha256):
        # Operator selects a known remote task after comparing account history.
        # This method never creates or retries a remote operation.
        with self._db() as c:
            row = c.execute('SELECT * FROM stages WHERE job_id=? AND stage=?', (job_id, stage)).fetchone()
        if not row or row['status'] != 'SUBMISSION_UNKNOWN' or row['request_sha'] != request_sha256:
            raise ForgeError('RECONCILIATION_REQUEST_IDENTITY_MISMATCH')
        data = self._task(stage, task_id)
        if not row['remote_name'] or data.get('name') != row['remote_name']:
            raise ForgeError('REMOTE_TASK_NAME_NOT_BOUND_TO_LOCAL_INTENT')
        with self._db() as c:
            c.execute('BEGIN IMMEDIATE')
            try:
                changed = c.execute('UPDATE stages SET task_id=?,status=?,actual=?,updated=? WHERE job_id=? AND stage=? AND status="SUBMISSION_UNKNOWN" AND request_sha=?',
                                    (task_id, data['status'], data.get('consumed_credits'), time.time(), job_id, stage, request_sha256)).rowcount
            except sqlite3.IntegrityError:
                raise ForgeError('REMOTE_TASK_ALREADY_REGISTERED') from None
            if changed != 1:
                raise ForgeError('RECONCILIATION_CONCURRENT_STATE_CHANGED')
            self._event(c, job_id, 'UNKNOWN_RECONCILED', {'stage': stage, 'task_id': task_id, 'request_sha256': request_sha256})
        return self.get_job(job_id)

    def download(self, job_id, stage, format='glb'):
        if stage not in STAGES or (stage == 'prototype' and format != 'preview') or (stage == 'build' and format not in ('glb', 'obj', 'mtl', 'fbx', 'texture', 'thumbnail')):
            raise ForgeError('INVALID_DOWNLOAD_FORMAT')
        with self._db() as c:
            row = c.execute('SELECT * FROM stages WHERE job_id=? AND stage=?', (job_id, stage)).fetchone()
        if not row or row['status'] != 'SUCCEEDED' or not row['task_id']:
            raise ForgeError('TASK_NOT_SUCCEEDED')
        name = 'preview.png' if stage == 'prototype' else {'texture': 'texture_0.png', 'thumbnail': 'thumbnail.png'}.get(format, 'model.' + format)
        target = self._workspace_path(self.root / 'jobs' / job_id / name, strict=False)
        if target.exists():
            if not target.is_file() or not target.stat().st_size:
                raise ForgeError('CACHED_ASSET_INVALID')
            with self._db() as c:
                receipt = c.execute('SELECT * FROM download_receipts WHERE job_id=? AND stage=? AND format=?', (job_id, stage, format)).fetchone()
            if not receipt or receipt['task_id'] != row['task_id'] or receipt['path'] != str(target):
                raise ForgeError('CACHED_ASSET_UNREGISTERED_REQUIRES_VALIDATION')
            if digest(target) != receipt['sha256'] or target.stat().st_size != receipt['bytes']:
                raise ForgeError('CACHED_ASSET_CONTENT_CHANGED_PRESERVE_AND_REPAIR_DERIVATIVE')
            return {'file': str(target), 'sha256': receipt['sha256'], 'bytes': receipt['bytes'], 'cached': True}
        data = self._task(stage, row['task_id'])
        if data['status'] != 'SUCCEEDED':
            raise ForgeError('REMOTE_TASK_NOT_SUCCEEDED')
        if stage == 'prototype':
            urls = data.get('image_urls') or []
            if len(urls) != 1:
                raise ForgeError('PROTOTYPE_IMAGE_NOT_UNIQUE')
            url, name = urls[0], 'preview.png'
        elif format == 'texture':
            textures = data.get('texture_urls') or []
            if len(textures) != 1 or not isinstance(textures[0], dict):
                raise ForgeError('TEXTURE_LAYOUT_REQUIRES_EXPLICIT_SELECTION')
            url, name = textures[0].get('base_color'), 'texture_0.png'
        elif format == 'thumbnail':
            url, name = data.get('thumbnail_url'), 'thumbnail.png'
        else:
            url, name = (data.get('model_urls') or {}).get(format), 'model.' + format
        if not safe_asset_url(url):
            raise ForgeError('ASSET_HOST_NOT_ALLOWED_OR_MISSING_URL')
        fd, temp = tempfile.mkstemp(prefix=name + '.', suffix='.part', dir=target.parent)
        part = Path(temp)
        try:
            opener = build_opener(SafeRedirect())
            with os.fdopen(fd, 'wb') as out, opener.open(Request(url, headers={'User-Agent': 'KAI-Meshy-Forge/0.2'}), timeout=120) as response:
                if not safe_asset_url(response.geturl()):
                    raise ForgeError('INVALID_ASSET_REDIRECT')
                total = 0
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    total += len(block)
                    if total > 512 * 1024 * 1024:
                        raise ForgeError('ASSET_TOO_LARGE')
                    out.write(block)
                out.flush(); os.fsync(out.fileno())
            if total == 0:
                raise ForgeError('ASSET_EMPTY')
            if format in {'preview', 'texture', 'thumbnail'}:
                self._decode_image(part)
            elif format in {'glb', 'obj', 'fbx'}:
                from .assets import inspect_model
                inspect_model(part, format_hint=format)
            # Android Python omits os.link. Exclusive creation preserves originals;
            # only the committed SQLite receipt makes these bytes usable as an asset.
            # An interrupted copy stays unregistered and is never accepted as cache.
            try:
                final_fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                self._workspace_path(target)
                if digest(target) != digest(part):
                    raise ForgeError('CONCURRENT_ASSET_CONTENT_CONFLICT') from None
            else:
                with os.fdopen(final_fd, 'wb') as out, part.open('rb') as source:
                    shutil.copyfileobj(source, out, 1024 * 1024)
                    out.flush(); os.fsync(out.fileno())
                if digest(target) != digest(part):
                    raise ForgeError('ASSET_COPY_INTEGRITY_FAILURE_PRESERVE_FOR_RECOVERY')
            result = {'file': str(target), 'sha256': digest(target), 'bytes': target.stat().st_size}
            with self._db() as c:
                c.execute('INSERT INTO download_receipts VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(job_id,stage,format) DO UPDATE SET task_id=excluded.task_id,path=excluded.path,sha256=excluded.sha256,bytes=excluded.bytes,created=excluded.created',
                          (job_id, stage, format, row['task_id'], str(target), result['sha256'], result['bytes'], time.time()))
                self._event(c, job_id, 'ASSET_DOWNLOADED', {'stage': stage, 'format': format, 'sha256': result['sha256'], 'bytes': result['bytes']})
            return result
        finally:
            part.unlink(missing_ok=True)
