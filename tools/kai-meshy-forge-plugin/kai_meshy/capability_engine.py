"""Catalogue-bound operations on the existing Forge ledger and private workspace.

No public URL, HTTP method, credential, shell, or independently owned ledger.
Creating a plan is local. Every remote create is one explicit durable intent.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import time
import shutil
import stat
import zipfile
from pathlib import PurePosixPath
from urllib.request import Request, build_opener

from .core import (COMMITTED_SQL, JOB_ID, TASK_ID, STATUSES, ForgeError,
                   _credits, _no_symlink, digest, public_json, safe_asset_url, unwrap, SafeRedirect)
from .registry import AssetRegistry

STAGE_PREFIX = 'op:'
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_REFERENCE_BYTES = 100_000_000
FORBIDDEN_KEYS = {'api_key', 'authorization', 'access_token', 'refresh_token', 'password',
                  'credential', 'credentials', 'base_url', 'base_url_v1', 'base_url_v2'}
SECRET = re.compile(r'(?i)(?:\bmsy_[A-Za-z0-9_-]{20,}|\bBearer\s+\S+|-----BEGIN .*PRIVATE KEY-----)')
MIMES = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp',
         '.glb': 'model/gltf-binary', '.gltf': 'model/gltf+json', '.obj': 'text/plain',
         '.fbx': 'application/octet-stream', '.stl': 'model/stl', '.3mf': 'model/3mf'}
OUTPUT_VARIANTS = {
    'rigged_character_glb': ('glb', ('result','rigged_character_glb_url')),
    'rigged_character_fbx': ('fbx', ('result','rigged_character_fbx_url')),
    'animation_glb': ('glb', ('result','animation_glb_url')),
    'animation_fbx': ('fbx', ('result','animation_fbx_url')),
    'processed_usdz': ('usdz', ('result','processed_usdz_url')),
    'processed_armature_fbx': ('fbx', ('result','processed_armature_fbx_url')),
    'processed_animation_fps_fbx': ('fbx', ('result','processed_animation_fps_fbx_url')),
    **{name: (name.rsplit('_',1)[-1], ('result','basic_animations',name+'_url')) for name in
       ('walking_glb','walking_fbx','walking_armature_glb','running_glb','running_fbx','running_armature_glb')},
}


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf8')
    except (TypeError, ValueError):
        raise ForgeError('OPERATION_JSON_INVALID') from None


def _sha(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


class CapabilityEngine:
    """The catalogue is injected in tests; production uses the bundled contracts."""
    def __init__(self, forge, catalog=None, *, max_operation_credits=None):
        self.forge = forge
        self._max_operation_credits = _credits(forge.max_credits if max_operation_credits is None else max_operation_credits)
        if self._max_operation_credits > forge.max_credits:
            raise ForgeError('OPERATION_CREDIT_CEILING_EXCEEDS_FORGE_AUTHORITY')
        if catalog is None:
            from .contracts import CapabilityCatalog
            catalog = CapabilityCatalog()
        self.catalog = catalog
        self.registry = AssetRegistry(forge)
        self._migrate()

    @property
    def max_operation_credits(self):
        """Operator-injected ceiling; deliberately absent from public tool inputs."""
        return self._max_operation_credits

    def _migrate(self):
        with self.forge._db() as c:
            jobs = {r['name'] for r in c.execute('PRAGMA table_info(jobs)')}
            if 'workflow_kind' not in jobs:
                c.execute('ALTER TABLE jobs ADD COLUMN workflow_kind TEXT NOT NULL DEFAULT "brick"')
            cols = {r['name'] for r in c.execute('PRAGMA table_info(stages)')}
            additions = {'capability_id': 'TEXT', 'operation_id': 'TEXT', 'manifest_path': 'TEXT',
                         'manifest_sha': 'TEXT', 'contract_sha': 'TEXT', 'contract_version': 'TEXT',
                         'dependencies_json': 'TEXT NOT NULL DEFAULT "[]"', 'quote_json': 'TEXT',
                         'checkpoint_json': 'TEXT', 'poll_attempts': 'INTEGER NOT NULL DEFAULT 0', 'approval_json': 'TEXT', 'model_json': 'TEXT'}
            for name, definition in additions.items():
                if name not in cols:
                    c.execute('ALTER TABLE stages ADD COLUMN ' + name + ' ' + definition)

    @staticmethod
    def _ids(job_id, operation_id):
        if not isinstance(job_id, str) or not JOB_ID.fullmatch(job_id) or not isinstance(operation_id, str) or not JOB_ID.fullmatch(operation_id):
            raise ForgeError('OPERATION_ID_INVALID')
        return STAGE_PREFIX + operation_id

    def _contract(self, capability_id):
        try:
            value = self.catalog.describe(capability_id)
        except (KeyError, ValueError):
            raise ForgeError('CAPABILITY_NOT_IN_CATALOGUE') from None
        if not isinstance(value, dict) or not value.get('routes', {}).get('create'):
            raise ForgeError('CAPABILITY_HAS_NO_REMOTE_CREATE_CONTRACT')
        return value

    def list_capabilities(self):
        return self.catalog.list()

    def describe(self, capability_id):
        return self.catalog.describe(capability_id)

    def _row(self, job_id, operation_id, c=None):
        stage = self._ids(job_id, operation_id)
        if c is None:
            with self.forge._db() as con:
                return self._row(job_id, operation_id, con)
        row = c.execute('SELECT * FROM stages WHERE job_id=? AND stage=?', (job_id, stage)).fetchone()
        if not row or not row['capability_id']:
            raise ForgeError('OPERATION_NOT_FOUND')
        return row

    def get_operation(self, job_id, operation_id='main'):
        row = self._row(job_id, operation_id)
        keys = ('job_id', 'operation_id', 'capability_id', 'stage', 'status', 'task_id', 'reservation',
                'actual', 'request_sha', 'manifest_sha', 'contract_sha', 'contract_version', 'remote_name', 'poll_attempts')
        result = {k: row[k] for k in keys}
        for field, name in [('dependencies_json', 'dependencies'), ('quote_json', 'quote'), ('checkpoint_json', 'checkpoint'), ('approval_json', 'approval'), ('model_json', 'model')]:
            result[name] = json.loads(row[field]) if row[field] else None
        return public_json(result)

    def list_operations(self, job_id):
        with self.forge._db() as c:
            rows = c.execute('SELECT operation_id FROM stages WHERE job_id=? AND capability_id IS NOT NULL ORDER BY intent_at,stage', (job_id,)).fetchall()
        return [self.get_operation(job_id, row['operation_id']) for row in rows]

    def _read_manifest(self, row):
        path = self.forge._workspace_path(row['manifest_path'])
        if path.stat().st_size > MAX_MANIFEST_BYTES or digest(path) != row['manifest_sha']:
            raise ForgeError('IMMUTABLE_OPERATION_MANIFEST_CHANGED')
        try:
            value = json.loads(path.read_text())
        except (ValueError, UnicodeError):
            raise ForgeError('OPERATION_MANIFEST_INVALID') from None
        return value

    @staticmethod
    def _safe_parameters(value, depth=0):
        if depth > 12:
            raise ForgeError('OPERATION_PARAMETERS_TOO_DEEP')
        if isinstance(value, dict):
            if len(value) > 100 or any(not isinstance(k, str) or k.lower() in FORBIDDEN_KEYS for k in value):
                raise ForgeError('OPERATION_PARAMETER_FIELDS_DENIED')
            for v in value.values():
                CapabilityEngine._safe_parameters(v, depth + 1)
        elif isinstance(value, list):
            if len(value) > 100:
                raise ForgeError('OPERATION_PARAMETER_ARRAY_TOO_LONG')
            for v in value:
                CapabilityEngine._safe_parameters(v, depth + 1)
        elif isinstance(value, str):
            if len(value) > 100_000 or SECRET.search(value):
                raise ForgeError('OPERATION_SECRET_OR_OVERSIZE_VALUE_DENIED')
        elif isinstance(value, float) and not math.isfinite(value):
            raise ForgeError('OPERATION_NONFINITE_VALUE_DENIED')
        elif value is not None and not isinstance(value, (int, float, bool)):
            raise ForgeError('OPERATION_PARAMETER_TYPE_DENIED')

    def _copy_reference(self, value, kind, folder, spec=None):
        if set(value) - {'local_path', 'parent_asset_id'} or not isinstance(value.get('local_path'), str):
            raise ForgeError('LOCAL_REFERENCE_OBJECT_INVALID')
        source = _no_symlink(value['local_path']).resolve(strict=True)
        if not any(source.is_relative_to(root) for root in self.forge.reference_roots):
            raise ForgeError('REFERENCE_OUTSIDE_APPROVED_ROOTS')
        if not source.is_file() or source.suffix.lower() not in MIMES or not 0 < source.stat().st_size <= 100 * 1024 * 1024:
            raise ForgeError('REFERENCE_FORMAT_OR_SIZE_NOT_ALLOWED')
        if kind == 'image':
            self.forge._source_bytes(source)
        elif kind != 'model':
            raise ForgeError('LOCAL_REFERENCE_FIELD_NOT_IN_CONTRACT')
        sha = digest(source)
        target = self.forge._workspace_path(folder / (sha + source.suffix.lower()), strict=False)
        if not target.exists():
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as out, source.open('rb') as src:
                copied = 0
                while True:
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    copied += len(chunk)
                    if copied > MAX_REFERENCE_BYTES:
                        raise ForgeError('REFERENCE_GROWTH_EXCEEDED_LIMIT')
                    out.write(chunk)
                out.flush(); os.fsync(out.fileno())
        if digest(target) != sha:
            raise ForgeError('LOCAL_REFERENCE_COPY_CHANGED')
        if kind == 'model' and target.suffix.lower() in {'.glb','.obj','.fbx'}:
            from .assets import inspect_model
            inspect_model(target)
        parent = value.get('parent_asset_id')
        if parent:
            self.registry.get(parent)
        asset_id = 'sha256-' + sha
        try:
            asset = self.registry.get(asset_id)
        except ForgeError as exc:
            if str(exc) != 'ASSET_NOT_FOUND':
                raise
            asset = self.registry.register(target, 'reference' if kind == 'image' else 'model', parent_id=parent,
                                           provenance={'source_id': 'local-authorized-reference', 'document_state': 'STAGING'})
        mime = self._reference_mime(source, spec or {})
        return {'asset_id': asset['id'], 'local_copy': str(target), 'sha256': sha,
                'mime': mime, 'kind': kind}

    @staticmethod
    def _reference_mime(path, spec):
        suffix = path.suffix.lower()
        native = MIMES.get(suffix)
        if not native:
            raise ForgeError('LOCAL_REFERENCE_FORMAT_NOT_SUPPORTED')
        extensions = spec.get('public_url_extensions')
        if spec.get('kind') == 'model' and extensions and suffix not in extensions:
            raise ForgeError('LOCAL_MODEL_FORMAT_NOT_SUPPORTED_FOR_CAPABILITY')
        allowed = spec.get('data_uri_mime_types')
        preferred = spec.get('preferred_data_uri_mime')
        if not allowed:
            return preferred or native
        if native in allowed:
            return native
        if spec.get('kind') == 'model' and preferred == 'application/octet-stream' and preferred in allowed:
            return preferred
        raise ForgeError('LOCAL_REFERENCE_INLINE_MIME_NOT_SUPPORTED_FOR_CAPABILITY')

    def _preflight(self, capability_id, parameters, contract):
        if not isinstance(parameters, dict):
            raise ForgeError('OPERATION_PARAMETERS_MUST_BE_OBJECT')
        self._safe_parameters(parameters)
        props = contract.get('request_schema', {}).get('properties', {})
        if props and set(parameters) - set(props):
            raise ForgeError('OPERATION_UNKNOWN_PARAMETER_FIELD')
        size = 0
        def substitute(value, spec):
            nonlocal size
            kind = spec.get('kind')
            if isinstance(value, dict) and 'reference' in value:
                raise ForgeError('INTERNAL_REFERENCE_OBJECT_CANNOT_BE_SUPPLIED')
            if isinstance(value, dict) and 'local_path' in value:
                if kind not in {'image','model'} or not isinstance(value['local_path'], str):
                    raise ForgeError('LOCAL_REFERENCE_FIELD_NOT_IN_CONTRACT')
                path = _no_symlink(value['local_path']).resolve(strict=True)
                if not any(path.is_relative_to(root) for root in self.forge.reference_roots) or not path.is_file():
                    raise ForgeError('REFERENCE_OUTSIDE_APPROVED_ROOTS')
                count = path.stat().st_size
                if count <= 0 or count > spec.get('data_uri_max_bytes', MAX_REFERENCE_BYTES):
                    raise ForgeError('REFERENCE_CONTRACT_BYTE_LIMIT_EXCEEDED')
                size += count
                if size > MAX_REFERENCE_BYTES:
                    raise ForgeError('OPERATION_REFERENCE_BYTE_BUDGET_EXCEEDED')
                mime = self._reference_mime(path, spec)
                return 'data:image/png;base64,iVBORw0KGgo=' if kind == 'image' else 'data:' + mime + ';base64,Z2xURg=='
            if isinstance(value, dict) and 'task_from_operation' in value:
                return '00000000-0000-0000-0000-000000000000'
            if isinstance(value, dict) and 'task_asset' in value:
                ref = value['task_asset']
                return 'https://assets.meshy.ai/KAI_PENDING_MANAGED_ASSET.' + ('png' if kind == 'image' else ref.get('format','glb'))
            return value
        skeleton = {}
        for key, value in parameters.items():
            schema = props.get(key, {}); spec = contract.get('input_fields', {}).get(key, {})
            if isinstance(value, list):
                if len(value) > schema.get('maxItems', 100) or len(value) < schema.get('minItems', 0):
                    raise ForgeError('OPERATION_PARAMETER_ARRAY_CONTRACT_BOUND')
                skeleton[key] = [substitute(item, spec) for item in value] if spec.get('many') else value
            else:
                skeleton[key] = substitute(value, spec)
        # Validate cardinality, required fields, models and types before copying
        # reference bytes or materializing any base64 payload.
        self.catalog.validate(capability_id, skeleton)

    def _normalize_parameters(self, parameters, contract, folder):
        if not isinstance(parameters, dict):
            raise ForgeError('OPERATION_PARAMETERS_MUST_BE_OBJECT')
        self._safe_parameters(parameters)
        inputs = contract.get('input_fields', {})
        dependencies = set()
        def one(value, spec):
            kind = spec.get('kind')
            if isinstance(value, dict) and 'reference' in value:
                raise ForgeError('INTERNAL_REFERENCE_OBJECT_CANNOT_BE_SUPPLIED')
            if isinstance(value, dict) and 'local_path' in value:
                return {'reference': self._copy_reference(value, kind, folder, spec)}
            if isinstance(value, dict) and set(value) == {'task_from_operation'}:
                dep = value['task_from_operation']
                self._ids('VALID', dep); dependencies.add(dep)
                if kind != 'task_id':
                    raise ForgeError('TASK_REFERENCE_FIELD_NOT_IN_CONTRACT')
                return {'task_from_operation': dep}
            if isinstance(value, dict) and set(value) == {'task_asset'}:
                ref = value['task_asset']
                if not isinstance(ref, dict) or set(ref) - {'operation_id', 'format', 'texture_index'} or kind not in {'image', 'model'}:
                    raise ForgeError('TASK_ASSET_REFERENCE_INVALID')
                self._ids('VALID', ref.get('operation_id')); dependencies.add(ref['operation_id'])
                return {'task_asset': ref}
            if isinstance(value, str) and (value.startswith(('http://', 'https://', 'data:')) and kind in {'image', 'model'}):
                raise ForgeError('REMOTE_OR_INLINE_REFERENCE_MUST_BE_MANAGED_ASSET')
            return value
        normalized = {}
        for key, value in parameters.items():
            spec = inputs.get(key, {})
            if isinstance(value, list) and spec.get('many'):
                normalized[key] = [one(item, spec) for item in value]
            else:
                normalized[key] = one(value, spec)
        if len(_canonical(normalized)) > MAX_MANIFEST_BYTES // 2:
            raise ForgeError('OPERATION_MANIFEST_TOO_LARGE')
        return normalized, dependencies

    def _dependency(self, job_id, operation_id, *, ready):
        row = self._row(job_id, operation_id)
        if ready and (row['status'] != 'SUCCEEDED' or not row['task_id']):
            raise ForgeError('OPERATION_DEPENDENCY_NOT_SUCCEEDED')
        return row

    def _observe_parent(self, row):
        data = self._task(row) if row['capability_id'] else self.forge._task(row['stage'],row['task_id'])
        if data['status'] != 'SUCCEEDED':
            raise ForgeError('OPERATION_REMOTE_PARENT_NOT_SUCCEEDED')
        expires = data.get('expires_at')
        if expires is not None:
            _credits(expires)
            expires_seconds = expires / 1000 if expires > 100_000_000_000 else expires
            if expires_seconds <= time.time():
                raise ForgeError('OPERATION_PARENT_ASSETS_EXPIRED_PRESERVE_AND_REUPLOAD_DERIVATIVE')
        return data

    def _wire(self, job_id, parameters, contract, *, ready):
        inputs = contract.get('input_fields', {})
        def one(value, spec):
            if isinstance(value, dict) and set(value) == {'reference'}:
                ref = value['reference']; asset = self.registry.get(ref['asset_id'])
                path = self.forge._workspace_path(ref['local_copy'])
                if path.stat().st_size > MAX_REFERENCE_BYTES:
                    raise ForgeError('OPERATION_REFERENCE_BYTE_BUDGET_EXCEEDED')
                with path.open('rb') as source:
                    data = source.read(MAX_REFERENCE_BYTES+1)
                if len(data) > MAX_REFERENCE_BYTES:
                    raise ForgeError('OPERATION_REFERENCE_BYTE_BUDGET_EXCEEDED')
                if hashlib.sha256(data).hexdigest() != ref['sha256'] or asset['sha256'] != ref['sha256']:
                    raise ForgeError('IMMUTABLE_OPERATION_REFERENCE_CHANGED')
                return 'data:' + ref['mime'] + ';base64,' + base64.b64encode(data).decode('ascii')
            if isinstance(value, dict) and set(value) == {'task_from_operation'}:
                row = self._dependency(job_id, value['task_from_operation'], ready=ready)
                if ready:
                    self._observe_parent(row)
                return row['task_id'] or '00000000-0000-0000-0000-000000000000'
            if isinstance(value, dict) and set(value) == {'task_asset'}:
                ref = value['task_asset']; row = self._dependency(job_id, ref['operation_id'], ready=ready)
                if not ready:
                    return 'https://assets.meshy.ai/KAI_PENDING_MANAGED_ASSET.' + ('png' if spec.get('kind') == 'image' else ref.get('format', 'glb'))
                task = self._observe_parent(row)
                return self._asset_url(task, ref.get('format', 'glb'), ref.get('texture_index', 0))
            if spec.get('kind') == 'task_id' and isinstance(value, str) and ready:
                with self.forge._db() as c:
                    tracked = c.execute('SELECT * FROM stages WHERE job_id=? AND task_id=?', (job_id, value)).fetchone()
                if not tracked or tracked['status'] != 'SUCCEEDED':
                    raise ForgeError('INPUT_TASK_NOT_SUCCEEDED_IN_SAME_JOB')
                self._observe_parent(tracked)
            return value
        result = {}
        for key, value in parameters.items():
            spec = inputs.get(key, {})
            result[key] = [one(item, spec) for item in value] if isinstance(value, list) and spec.get('many') else one(value, spec)
        return result

    def _validate_quote(self, capability_id, wire, context=None):
        try:
            normalized = self.catalog.validate(capability_id, wire, context=context)
            quote = self.catalog.quote(capability_id, normalized, context=context)
        except ValueError:
            raise ForgeError('OPERATION_CONTRACT_VALIDATION_FAILED') from None
        if not isinstance(normalized, dict) or not isinstance(quote, dict):
            raise ForgeError('OPERATION_CONTRACT_RESPONSE_INVALID')
        return normalized, quote

    def _parent_context(self, job_id, wire, contract):
        task_ids = [value for key, value in wire.items() if contract.get('input_fields', {}).get(key, {}).get('kind') == 'task_id' and isinstance(value, str)]
        if len(task_ids) != 1:
            return None
        with self.forge._db() as c:
            parent = c.execute('SELECT * FROM stages WHERE job_id=? AND task_id=?', (job_id, task_ids[0])).fetchone()
        if not parent:
            return None
        info = {'operation_id': parent['capability_id'] or 'creative_lab.brick_figure.' + parent['stage'],
                'status': parent['status'], 'task_id': parent['task_id'], 'candidate_ids': [parent['task_id']],
                'account_verified': True}
        if parent['model_json']:
            info.update(json.loads(parent['model_json']))
        return {'parent': info}

    def create_operation(self, job_id, capability_id, parameters, budget=500, operation_id='main',
                         dependencies=(), parent_asset_ids=()):
        stage = self._ids(job_id, operation_id)
        if isinstance(budget, bool) or not isinstance(budget, int) or not 1 <= budget <= self.forge.max_credits:
            raise ForgeError('JOB_BUDGET_OUTSIDE_AUTHORIZED_LIMIT')
        contract = self._contract(capability_id)
        with self.forge._db() as c:
            existing = c.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
            if existing and (existing['rejected'] or existing['local_cancelled']):
                raise ForgeError('JOB_CANCELLED_OR_REJECTED')
        if isinstance(dependencies, (str, bytes)) or len(dependencies) > 100:
            raise ForgeError('OPERATION_DEPENDENCIES_INVALID')
        for parent in parent_asset_ids:
            self.registry.get(parent)
        self._preflight(capability_id, parameters, contract)
        folder = self.forge._workspace_path(self.forge.root / 'jobs' / job_id / 'operations' / operation_id, strict=False)
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        parameters, discovered = self._normalize_parameters(parameters, contract, folder)
        deps = sorted(set(dependencies) | discovered)
        if operation_id in deps:
            raise ForgeError('OPERATION_SELF_DEPENDENCY_DENIED')
        for dep in deps:
            self._dependency(job_id, dep, ready=False)
        wire = self._wire(job_id, parameters, contract, ready=False)
        _, quote = self._validate_quote(capability_id, wire)
        manifest = {'schema': 'kai.meshy.operation/1', 'job_id': job_id, 'operation_id': operation_id,
                    'capability_id': capability_id, 'parameters': parameters, 'dependencies': deps,
                    'parent_asset_ids': sorted(parent_asset_ids), 'contract_sha': _sha(contract)}
        raw = _canonical(manifest); source_sha = hashlib.sha256(raw).hexdigest()
        path = self.forge._workspace_path(folder / 'request.json', strict=False)
        if path.exists():
            if digest(path) != source_sha:
                raise ForgeError('IMMUTABLE_OPERATION_IDENTITY_CONFLICT')
        else:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as out:
                out.write(raw); out.flush(); os.fsync(out.fileno())
        with self.forge._db() as c:
            c.execute('BEGIN IMMEDIATE')
            job = c.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
            if job and (job['rejected'] or job['local_cancelled']):
                raise ForgeError('JOB_CANCELLED_OR_REJECTED')
            if job and job['budget'] != budget:
                raise ForgeError('EXISTING_JOB_BUDGET_CONFLICT')
            if not job:
                c.execute('INSERT INTO jobs(id,source,source_sha,budget,created,workflow_kind) VALUES(?,?,?,?,?,?)',
                          (job_id, str(path), source_sha, budget, time.time(), 'capability'))
            elif job['workflow_kind'] == 'brick':
                c.execute('UPDATE jobs SET workflow_kind="mixed" WHERE id=?', (job_id,))
            old = c.execute('SELECT manifest_sha FROM stages WHERE job_id=? AND stage=?', (job_id, stage)).fetchone()
            if old:
                if old['manifest_sha'] != source_sha:
                    raise ForgeError('EXISTING_OPERATION_IDENTITY_CONFLICT')
            else:
                c.execute('INSERT INTO stages(job_id,stage,status,reservation,intent_at,updated,source_sha,capability_id,operation_id,manifest_path,manifest_sha,contract_sha,contract_version,dependencies_json,quote_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                          (job_id, stage, 'PLANNED', 0, time.time(), time.time(), source_sha, capability_id,
                           operation_id, str(path), source_sha, _sha(contract), str(quote.get('contract_version', 'UNSPECIFIED')),
                           json.dumps(deps), json.dumps(public_json(quote), sort_keys=True)))
                self.forge._event(c, job_id, 'OPERATION_PLANNED', {'operation_id': operation_id, 'capability_id': capability_id, 'manifest_sha': source_sha})
        return self.get_operation(job_id, operation_id)

    def _ready(self, c, row, price, payload, contract):
        job = c.execute('SELECT * FROM jobs WHERE id=?', (row['job_id'],)).fetchone()
        if not job or job['local_cancelled'] or job['rejected']:
            raise ForgeError('JOB_CANCELLED_OR_REJECTED')
        if row['status'] != 'PLANNED' or row['task_id']:
            raise ForgeError('OPERATION_ALREADY_SUBMITTED_NEVER_REPEAT_POST')
        for dep in json.loads(row['dependencies_json']):
            dependency = self._row(row['job_id'], dep, c)
            if dependency['status'] != 'SUCCEEDED' or not dependency['task_id']:
                raise ForgeError('OPERATION_DEPENDENCY_NOT_SUCCEEDED')
        for field, spec in contract.get('input_fields', {}).items():
            if spec.get('kind') != 'task_id' or field not in payload:
                continue
            values = payload[field] if spec.get('many') else [payload[field]]
            for task_id in values:
                parent = c.execute('SELECT * FROM stages WHERE job_id=? AND task_id=?', (row['job_id'],task_id)).fetchone()
                if not parent or parent['status'] != 'SUCCEEDED':
                    raise ForgeError('OPERATION_PARENT_NOT_SUCCEEDED_IN_SAME_JOB')
                allowed = spec.get('allowed_parent_capabilities')
                actual = parent['capability_id'] or 'creative_lab.brick_figure.' + parent['stage']
                if allowed and actual not in allowed:
                    raise ForgeError('OPERATION_PARENT_FIELD_PRODUCT_MISMATCH')
        constraints = contract.get('parent_constraints', {})
        if constraints:
            ids = [value for key, value in payload.items() if contract.get('input_fields', {}).get(key, {}).get('kind') == 'task_id' and isinstance(value, str)]
            if len(ids) != 1:
                raise ForgeError('OPERATION_PARENT_TASK_NOT_UNIQUE')
            parent = c.execute('SELECT * FROM stages WHERE job_id=? AND task_id=?', (row['job_id'], ids[0])).fetchone()
            expected = constraints.get('operation_id')
            actual = parent['capability_id'] if parent else None
            if parent and not actual and parent['stage'] in {'prototype', 'build'}:
                actual = 'creative_lab.brick_figure.' + parent['stage']
            if not parent or parent['status'] != constraints.get('status', 'SUCCEEDED') or expected and actual != expected:
                raise ForgeError('OPERATION_PARENT_PRODUCT_OR_STATUS_MISMATCH')
            if constraints.get('human_visual_gate'):
                if parent['capability_id']:
                    approval = json.loads(parent['approval_json']) if parent['approval_json'] else None
                    if not approval or not approval.get('actor') or not approval.get('preview_path') or approval.get('task_id') != parent['task_id']:
                        raise ForgeError('OPERATION_PARENT_VISUAL_APPROVAL_REQUIRED')
                    asset = self.registry.get(approval['asset_id'])
                    if asset['sha256'] != approval['sha256']:
                        raise ForgeError('OPERATION_APPROVED_PARENT_PREVIEW_CHANGED')
                    preview = self.forge._workspace_path(approval['preview_path'])
                    if digest(preview) != approval['sha256'] or approval['task_id'] != parent['task_id']:
                        raise ForgeError('OPERATION_APPROVED_PARENT_PREVIEW_CHANGED')
                else:
                    if not job['preview_approved'] or not job['approved_actor'] or not job['approved_preview_sha']:
                        raise ForgeError('OPERATION_PARENT_VISUAL_APPROVAL_REQUIRED')
                    preview = self.forge._workspace_path(self.forge.root / 'jobs' / row['job_id'] / 'preview.png')
                    if digest(preview) != job['approved_preview_sha']:
                        raise ForgeError('OPERATION_APPROVED_PARENT_PREVIEW_CHANGED')
        job_cost = c.execute('SELECT coalesce(sum(' + COMMITTED_SQL + '),0) FROM stages WHERE job_id=?', (row['job_id'],)).fetchone()[0]
        total = c.execute('SELECT coalesce(sum(' + COMMITTED_SQL + '),0) FROM stages').fetchone()[0]
        if job_cost + price > job['budget'] or total + price > self.forge.max_credits:
            raise ForgeError('OPERATION_BUDGET_EXCEEDED')

    def submit_operation(self, job_id, operation_id='main'):
        row = self._row(job_id, operation_id); contract = self._contract(row['capability_id'])
        if not self.forge.spending_enabled or job_id not in self.forge.spending_job_ids:
            raise ForgeError('OPERATION_SPENDING_DISABLED_OR_JOB_NOT_AUTHORIZED')
        if row['contract_sha'] != _sha(contract):
            raise ForgeError('OPERATION_CONTRACT_CHANGED_REPLAN_REQUIRED')
        manifest = self._read_manifest(row)
        wire = self._wire(job_id, manifest['parameters'], contract, ready=True)
        context = self._parent_context(job_id, wire, contract)
        payload, quote = self._validate_quote(row['capability_id'], wire, context=context)
        if quote.get('price_status') != 'EXACT' or quote.get('spend_allowed') is not True or quote.get('credits') is None:
            raise ForgeError('EXACT_VERIFIED_PRICE_REQUIRED')
        price = _credits(quote['credits'])
        if price > self._max_operation_credits:
            raise ForgeError('OPERATION_EXACT_PRICE_EXCEEDS_OPERATOR_CEILING')
        identity = {'job_id': job_id, 'operation_id': operation_id, 'capability_id': row['capability_id'],
                    'manifest_sha': row['manifest_sha'], 'parent_tasks': {}, 'contract_sha': row['contract_sha']}
        for dep in manifest['dependencies']:
            identity['parent_tasks'][dep] = self._dependency(job_id, dep, ready=True)['task_id']
        remote_name = 'KAI-' + _sha(identity)[:48]
        properties = contract.get('request_schema', {}).get('properties', {})
        if 'name' in properties:
            payload['name'] = remote_name
            payload, final_quote = self._validate_quote(row['capability_id'], payload, context=context)
            if final_quote.get('price_status') != 'EXACT' or final_quote.get('spend_allowed') is not True or final_quote.get('credits') != price:
                raise ForgeError('OPERATION_QUOTE_CHANGED_DURING_PREFLIGHT')
            quote = final_quote
        else:
            remote_name = None
        request_sha = _sha(payload)
        auth = self.forge.cli.auth()
        if auth.get('authenticated') is not True or auth.get('verified') is not True:
            raise ForgeError('ACCOUNT_NOT_VERIFIED')
        if _credits(self.forge.cli.balance().get('balance')) < price:
            raise ForgeError('INSUFFICIENT_API_BALANCE')
        with self.forge._db() as c:
            c.execute('BEGIN IMMEDIATE')
            latest = self._row(job_id, operation_id, c)
            self._ready(c, latest, price, payload, contract)
            self._read_manifest(latest)
            model = {k:v for k,v in payload.items() if k in {'ai_model','model_type','geometry_resolution','texture_resolution','hd_texture','ultra_mode'}}
            c.execute('UPDATE stages SET status="SUBMISSION_UNKNOWN",reservation=?,request_sha=?,remote_name=?,quote_json=?,model_json=?,intent_at=?,updated=? WHERE job_id=? AND stage=?',
                      (price, request_sha, remote_name, json.dumps(public_json(quote)), json.dumps(model), time.time(), time.time(), job_id, row['stage']))
            self.forge._event(c, job_id, 'OPERATION_SUBMISSION_INTENT', {'operation_id': operation_id, 'request_sha': request_sha, 'reserved': price})
        try:
            result = unwrap(self.forge.cli.request(contract, 'create', payload=payload))
            task_id = result if isinstance(result, str) else result.get('id') if isinstance(result, dict) else None
            if not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id):
                raise ForgeError('OPERATION_CREATE_REPLY_INVALID')
            with self.forge._db() as c:
                c.execute('BEGIN IMMEDIATE')
                duplicate = c.execute('SELECT 1 FROM stages WHERE task_id=? AND NOT(job_id=? AND stage=?)', (task_id, job_id, row['stage'])).fetchone()
                if duplicate:
                    raise ForgeError('OPERATION_REMOTE_ID_ALREADY_REGISTERED')
                c.execute('UPDATE stages SET task_id=?,status="PENDING",updated=? WHERE job_id=? AND stage=?', (task_id, time.time(), job_id, row['stage']))
                self.forge._event(c, job_id, 'OPERATION_SUBMISSION_CONFIRMED', {'operation_id': operation_id, 'task_id': task_id})
        except Exception:
            raise ForgeError('OPERATION_SUBMISSION_UNKNOWN_RECONCILE_NEVER_REPEAT_POST') from None
        return self.get_operation(job_id, operation_id)

    def _task(self, row, timeout=None):
        if not row['task_id'] or not TASK_ID.fullmatch(row['task_id']):
            raise ForgeError('OPERATION_TASK_UNKNOWN_RECONCILE_FIRST')
        contract = self._contract(row['capability_id'])
        kwargs = {'task_id': row['task_id']}
        if timeout is not None:
            kwargs['timeout'] = timeout
        data = unwrap(self.forge.cli.request(contract, 'get', **kwargs))
        if not isinstance(data, dict) or data.get('id') != row['task_id'] or data.get('status') not in STATUSES:
            raise ForgeError('OPERATION_REMOTE_ID_OR_STATE_MISMATCH')
        if data.get('consumed_credits') is not None:
            _credits(data['consumed_credits'])
        return data

    def get_remote(self, capability_id, task_id, timeout=30):
        self._contract(capability_id)
        task = self._task({'capability_id': capability_id, 'task_id': task_id}, timeout=timeout)
        result = public_json(task)
        variants = []
        for name, (_, parts) in OUTPUT_VARIANTS.items():
            value = task
            for part in parts:
                value = value.get(part) if isinstance(value,dict) else None
            if safe_asset_url(value):
                variants.append(name)
        result['available_model_formats'] = sorted(set((task.get('model_urls') or {}).keys()) | {OUTPUT_VARIANTS[name][0] for name in variants})
        result['available_output_variants'] = variants
        result['image_count'] = len(task.get('image_urls') or [])
        result['texture_set_count'] = len(task.get('texture_urls') or [])
        result['scope'] = 'VENDOR_GET_ONLY_LOCAL_LEDGER_UNCHANGED'
        return result

    def refresh_operation(self, job_id, operation_id='main', timeout=30):
        row = self._row(job_id, operation_id); task = self._task(row, timeout=timeout)
        with self.forge._db() as c:
            c.execute('BEGIN IMMEDIATE')
            latest = self._row(job_id, operation_id, c)
            if latest['task_id'] != row['task_id']:
                raise ForgeError('OPERATION_TASK_IDENTITY_CHANGED')
            if latest['status'] in {'SUCCEEDED', 'FAILED', 'CANCELED'}:
                if task['status'] != latest['status'] or (latest['actual'] is not None and task.get('consumed_credits') is not None and latest['actual'] != task['consumed_credits']):
                    raise ForgeError('OPERATION_TERMINAL_FACT_CHANGED_RECONCILE')
            checkpoint = {'status': task['status'], 'progress': task.get('progress'), 'task_id': row['task_id']}
            c.execute('UPDATE stages SET status=?,actual=coalesce(?,actual),checkpoint_json=?,poll_attempts=poll_attempts+1,updated=? WHERE job_id=? AND stage=?',
                      (task['status'], task.get('consumed_credits'), json.dumps(public_json(checkpoint)), time.time(), job_id, row['stage']))
            self.forge._event(c, job_id, 'OPERATION_TASK_OBSERVED', {'operation_id': operation_id, **checkpoint, 'consumed_credits': task.get('consumed_credits')})
        return self.get_operation(job_id, operation_id)

    def poll_operation(self, job_id, operation_id='main', timeout=60, interval=5, max_attempts=60, max_stalled=10):
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 3600 or not 0.05 <= interval <= 60 or not 1 <= max_attempts <= 1000 or not 1 <= max_stalled <= 1000:
            raise ForgeError('OPERATION_POLL_LIMITS_INVALID')
        end = time.monotonic() + timeout; previous = None; stalled = 0
        for attempt in range(max_attempts):
            if self.forge.get_job(job_id)['job']['local_cancelled']:
                return {'wait_stop': 'LOCAL_CANCEL_REMOTE_UNCHANGED', 'operation': self.get_operation(job_id, operation_id)}
            if time.monotonic() >= end:
                break
            remaining = end - time.monotonic()
            try:
                result = self.refresh_operation(job_id, operation_id, timeout=min(180, remaining))
            except ForgeError as exc:
                if str(exc) == 'CLI_UNAVAILABLE_OR_TIMED_OUT:TIMEOUTEXPIRED':
                    return {'wait_stop': 'READ_TIMEOUT_SAME_TASK_PRESERVED', 'operation': self.get_operation(job_id, operation_id)}
                raise
            if result['status'] in {'SUCCEEDED', 'FAILED', 'CANCELED'}:
                return result
            signature = (result['status'], (result.get('checkpoint') or {}).get('progress'))
            stalled = stalled + 1 if signature == previous else 0; previous = signature
            if stalled >= max_stalled:
                return {'wait_stop': 'NO_PROGRESS_RECONCILE_SAME_TASK', 'operation': result, 'attempts': attempt + 1}
            time.sleep(min(interval, max(0, end - time.monotonic())))
        return {'wait_stop': 'LIMIT_TASK_MAY_STILL_RUN', 'operation': self.get_operation(job_id, operation_id)}

    def checkpoint(self, job_id, operation_id, label, asset_ids=()):
        if not isinstance(label, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}', label) or len(asset_ids) > 100:
            raise ForgeError('OPERATION_CHECKPOINT_INVALID')
        assets = [{'id': asset_id, 'sha256': self.registry.get(asset_id)['sha256']} for asset_id in asset_ids]
        with self.forge._db() as c:
            row = self._row(job_id, operation_id, c)
            checkpoint = {'label': label, 'assets': assets, 'task_id': row['task_id'], 'status': row['status']}
            c.execute('UPDATE stages SET checkpoint_json=?,updated=? WHERE job_id=? AND stage=?', (json.dumps(checkpoint), time.time(), job_id, row['stage']))
            self.forge._event(c, job_id, 'OPERATION_CHECKPOINT', {'operation_id': operation_id, **checkpoint})
        return self.get_operation(job_id, operation_id)

    def approve_operation(self, job_id, operation_id, asset_id, actor):
        if not isinstance(actor, str) or not re.fullmatch(r'[\w .@-]{1,100}', actor):
            raise ForgeError('OPERATION_APPROVAL_ACTOR_REQUIRED')
        asset = self.registry.get(asset_id)
        row = self._row(job_id, operation_id)
        folder = Path(row['manifest_path']).parent / 'outputs'
        if row['status'] != 'SUCCEEDED':
            raise ForgeError('OPERATION_APPROVAL_REQUIRES_THIS_TASK_PREVIEW')
        with self.forge._db() as c:
            c.execute('BEGIN IMMEDIATE')
            job = c.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
            receipt = c.execute('SELECT * FROM download_receipts WHERE job_id=? AND stage=? AND task_id=? AND sha256=? AND format LIKE "image:%"', (job_id, row['stage'], row['task_id'], asset['sha256'])).fetchone()
            if not job or job['rejected'] or job['local_cancelled'] or not receipt:
                raise ForgeError('OPERATION_PREVIEW_APPROVAL_NOT_ALLOWED')
            preview = self.forge._workspace_path(receipt['path'])
            if not preview.is_relative_to(folder) or digest(preview) != asset['sha256']:
                raise ForgeError('OPERATION_APPROVAL_REQUIRES_THIS_TASK_PREVIEW')
            self.forge._decode_image(preview)
            approval = {'actor': actor, 'asset_id': asset_id, 'preview_path': str(preview), 'sha256': asset['sha256'], 'task_id': row['task_id'], 'approved_at': time.time()}
            c.execute('UPDATE stages SET approval_json=?,updated=? WHERE job_id=? AND stage=?', (json.dumps(approval), time.time(), job_id, row['stage']))
            self.forge._event(c, job_id, 'OPERATION_VISUAL_APPROVED', {'operation_id': operation_id, **approval})
        return self.get_operation(job_id, operation_id)

    def cancel_local(self, job_id, reason='user request'):
        return self.forge.cancel(job_id, reason)

    def reconcile_operation(self, job_id, operation_id, task_id, request_sha256, *, receipt_asset_id=None, actor=None):
        row = self._row(job_id, operation_id)
        if row['status'] != 'SUBMISSION_UNKNOWN' or row['request_sha'] != request_sha256 or not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id):
            raise ForgeError('OPERATION_RECONCILIATION_IDENTITY_MISMATCH')
        candidate = dict(row); candidate['task_id'] = task_id
        task = self._task(candidate)
        if row['remote_name']:
            if task.get('name') != row['remote_name']:
                raise ForgeError('OPERATION_REMOTE_NAME_MISMATCH')
            binding = 'MANAGED_REMOTE_NAME'
        else:
            if not receipt_asset_id or not isinstance(actor, str) or not re.fullmatch(r'[\w .@-]{1,100}', actor):
                raise ForgeError('OPERATION_RECONCILIATION_REQUIRES_OPERATOR_RECEIPT')
            asset = self.registry.get(receipt_asset_id)
            if asset['role'] != 'evidence':
                raise ForgeError('OPERATION_RECONCILIATION_RECEIPT_ROLE_INVALID')
            path = self.forge._workspace_path(asset['path'])
            if path.stat().st_size > 8192:
                raise ForgeError('OPERATION_RECONCILIATION_RECEIPT_TOO_LARGE')
            receipt = json.loads(path.read_text())
            expected = {'job_id': job_id, 'operation_id': operation_id, 'task_id': task_id, 'request_sha256': request_sha256, 'actor': actor, 'confirmed': True}
            if receipt != expected:
                raise ForgeError('OPERATION_RECONCILIATION_RECEIPT_MISMATCH')
            binding = 'EXPLICIT_OPERATOR_RECEIPT'
        with self.forge._db() as c:
            c.execute('BEGIN IMMEDIATE')
            duplicate = c.execute('SELECT 1 FROM stages WHERE task_id=?', (task_id,)).fetchone()
            if duplicate:
                raise ForgeError('OPERATION_REMOTE_ID_ALREADY_REGISTERED')
            changed = c.execute('UPDATE stages SET task_id=?,status=?,actual=?,updated=? WHERE job_id=? AND stage=? AND status="SUBMISSION_UNKNOWN" AND request_sha=?',
                                (task_id, task['status'], task.get('consumed_credits'), time.time(), job_id, row['stage'], request_sha256)).rowcount
            if changed != 1:
                raise ForgeError('OPERATION_RECONCILIATION_CONCURRENT_CHANGE')
            self.forge._event(c, job_id, 'OPERATION_UNKNOWN_RECONCILED', {'operation_id': operation_id, 'task_id': task_id, 'binding': binding, 'receipt_asset_id': receipt_asset_id, 'actor': actor})
        return self.get_operation(job_id, operation_id)

    def list_remote(self, capability_id, cursor=None, page_size=50, timeout=30):
        contract = self._contract(capability_id)
        schema = contract.get('list_query_schema', {}).get('properties', {})
        if isinstance(page_size, bool) or not isinstance(page_size, int) or not 1 <= page_size <= 100:
            raise ForgeError('REMOTE_LIST_PAGE_SIZE_INVALID')
        query = {}
        if 'page_size' in schema:
            query['page_size'] = page_size
        if cursor is not None:
            field = next((f for f in ('cursor', 'page_token', 'page_num') if f in schema), None)
            if not field or not isinstance(cursor, (str, int)) or isinstance(cursor, bool) or len(str(cursor)) > 512:
                raise ForgeError('REMOTE_LIST_CURSOR_NOT_IN_CONTRACT')
            query[field] = cursor
            if schema[field].get('type') == 'integer' and isinstance(cursor,str):
                if not cursor.isdigit():
                    raise ForgeError('REMOTE_LIST_NUMBERED_CURSOR_INVALID')
                query[field] = int(cursor)
        elif 'page_num' in schema:
            query['page_num'] = 1
        data = unwrap(self.forge.cli.request(contract, 'list', query=query, timeout=timeout))
        next_cursor = None; exhaustion = False
        if isinstance(data, list):
            tasks = data
        elif isinstance(data, dict):
            lists = [data[k] for k in ('result', 'tasks', 'data') if isinstance(data.get(k), list)]
            if len(lists) != 1:
                raise ForgeError('REMOTE_TASK_LIST_SHAPE_INVALID')
            tasks = lists[0]
            next_cursor = data.get('next_cursor', data.get('next_page_token', data.get('next_page_num')))
            exhaustion = any(key in data and data[key] is None for key in ('next_cursor','next_page_token','next_page_num'))
        else:
            raise ForgeError('REMOTE_TASK_LIST_SHAPE_INVALID')
        if len(tasks) > 1000 or any(not isinstance(task, dict) or not isinstance(task.get('id'), str) or not TASK_ID.fullmatch(task['id']) for task in tasks):
            raise ForgeError('REMOTE_TASK_LIST_ID_INVALID')
        if next_cursor is not None and (not isinstance(next_cursor, (str, int)) or isinstance(next_cursor, bool) or len(str(next_cursor)) > 512):
            raise ForgeError('REMOTE_TASK_LIST_CURSOR_INVALID')
        # Official Meshy list endpoints document page_num and return bare arrays.
        # Continue even after a short nonempty page; an empty numbered page is
        # the exhaustion observation. No cursor field is invented for APIs that
        # do not declare numbered pagination.
        if next_cursor is None and not exhaustion and 'page_num' in schema:
            if not tasks:
                exhaustion = True
            else:
                current = query.get('page_num', 1)
                if isinstance(current, str) and current.isdigit():
                    current = int(current)
                if not isinstance(current, int) or isinstance(current, bool) or current < 1:
                    raise ForgeError('REMOTE_LIST_NUMBERED_CURSOR_INVALID')
                next_cursor = current + 1
        allowed = {'id', 'status', 'progress', 'consumed_credits', 'created_at', 'finished_at', 'type'}
        return {'capability_id': capability_id, 'tasks': [public_json({k:v for k,v in task.items() if k in allowed}) for task in tasks],
                'next_cursor': next_cursor, 'scope': 'ONE_VERIFIED_PAGE', 'exhausted_available_pages': exhaustion, 'complete_history': False}

    def list_history(self, capability_id, max_pages=20, page_size=50):
        if isinstance(max_pages, bool) or not isinstance(max_pages, int) or not 1 <= max_pages <= 100:
            raise ForgeError('REMOTE_HISTORY_PAGE_LIMIT_INVALID')
        pages = []; seen = set(); cursor = None
        for _ in range(max_pages):
            page = self.list_remote(capability_id, cursor=cursor, page_size=page_size); pages.append(page)
            cursor = page['next_cursor']
            if cursor is None:
                exhausted = page.get('exhausted_available_pages', False)
                return {'pages': pages, 'scope': 'VERIFIED_SCOPE' if exhausted else 'PARTIAL',
                        'exhausted_available_pages': exhausted, 'complete_history': False,
                        'stop': 'AVAILABLE_LISTING_EXHAUSTED_RETENTION_APPLIES' if exhausted else 'NO_EXHAUSTION_PROOF'}
            marker = str(cursor)
            if marker in seen:
                return {'pages': pages, 'scope': 'PARTIAL', 'stop': 'REPEATED_CURSOR', 'complete_history': False}
            seen.add(marker)
        return {'pages': pages, 'scope': 'PARTIAL', 'stop': 'PAGE_LIMIT', 'complete_history': False}

    @staticmethod
    def _asset_url(task, format, texture_index=0, variant=None):
        if isinstance(texture_index, bool) or not isinstance(texture_index, int) or not 0 <= texture_index <= 100:
            raise ForgeError('OPERATION_TEXTURE_INDEX_INVALID')
        if variant is not None:
            spec = OUTPUT_VARIANTS.get(variant)
            if not spec or spec[0] != format:
                raise ForgeError('OPERATION_OUTPUT_VARIANT_OR_FORMAT_NOT_ALLOWED')
            url = task
            for part in spec[1]:
                url = url.get(part) if isinstance(url,dict) else None
        elif format in {'glb', 'gltf', 'fbx', 'obj', 'mtl', 'stl', '3mf', 'usdz', 'blend'}:
            url = (task.get('model_urls') or {}).get(format)
            if not url and isinstance(task.get('result'), dict):
                # Explicit response fields documented by Meshy rigging and animation.
                fields = {'glb':['rigged_character_glb_url','animation_glb_url'],
                          'fbx':['rigged_character_fbx_url','animation_fbx_url'],
                          'usdz':['processed_usdz_url']}.get(format, [])
                candidates = [task['result'][key] for key in fields if task['result'].get(key)]
                if len(candidates) > 1:
                    raise ForgeError('OPERATION_MULTIPLE_OUTPUT_VARIANTS_REQUIRE_SELECTION')
                url = candidates[0] if candidates else None
        elif format == 'thumbnail':
            url = task.get('thumbnail_url')
        elif format == 'image':
            values = task.get('image_urls') or []
            url = values[texture_index] if texture_index < len(values) else None
        elif format in {'base_color', 'metallic', 'normal', 'roughness'}:
            values = task.get('texture_urls') or []
            value = values[texture_index] if texture_index < len(values) else {}
            url = value.get(format) if isinstance(value, dict) else None
        else:
            raise ForgeError('OPERATION_ASSET_FORMAT_NOT_ALLOWED')
        if not safe_asset_url(url):
            raise ForgeError('OPERATION_ASSET_URL_NOT_ON_ALLOWED_CDN')
        return url

    def download_operation(self, job_id, operation_id='main', format='glb', texture_index=0, timeout=60, variant=None):
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 180:
            raise ForgeError('OPERATION_DOWNLOAD_TIMEOUT_INVALID')
        allowed = {'glb', 'gltf', 'fbx', 'obj', 'mtl', 'stl', '3mf', 'usdz', 'blend', 'thumbnail', 'image', 'base_color', 'metallic', 'normal', 'roughness'}
        if format not in allowed or isinstance(texture_index, bool) or not isinstance(texture_index, int) or not 0 <= texture_index <= 100:
            raise ForgeError('OPERATION_ASSET_FORMAT_OR_INDEX_INVALID')
        if variant is not None and (variant not in OUTPUT_VARIANTS or OUTPUT_VARIANTS[variant][0] != format):
            raise ForgeError('OPERATION_OUTPUT_VARIANT_OR_FORMAT_NOT_ALLOWED')
        row = self._row(job_id, operation_id)
        if row['status'] != 'SUCCEEDED' or not row['task_id']:
            raise ForgeError('OPERATION_ASSET_REQUIRES_SUCCEEDED_TASK')
        receipt_format = format + ':' + str(texture_index)
        if variant:
            receipt_format += ':' + variant
        folder = self.forge._workspace_path(Path(row['manifest_path']).parent / 'outputs', strict=False)
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.forge._db() as c:
            receipt = c.execute('SELECT * FROM download_receipts WHERE job_id=? AND stage=? AND format=?', (job_id, row['stage'], receipt_format)).fetchone()
        if receipt:
            target = self.forge._workspace_path(receipt['path'])
            if not target.is_relative_to(folder) or receipt['task_id'] != row['task_id'] or not target.is_file() or target.stat().st_size != receipt['bytes'] or digest(target) != receipt['sha256']:
                raise ForgeError('OPERATION_CACHED_ASSET_CHANGED_PRESERVE_FOR_RECOVERY')
            return {'path': str(target), 'sha256': receipt['sha256'], 'bytes': receipt['bytes'], 'cached': True,
                    'asset_id': 'sha256-' + receipt['sha256'], 'format': format, 'texture_index': texture_index}
        deadline = time.monotonic() + timeout
        task = self._task(row, timeout=min(180, timeout))
        if task['status'] != 'SUCCEEDED':
            raise ForgeError('OPERATION_REMOTE_TASK_NOT_SUCCEEDED')
        url = self._asset_url(task, format, texture_index, variant=variant)
        fd, name = tempfile.mkstemp(prefix='download-', suffix='.part', dir=folder)
        part = Path(name)
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                os.close(fd)
                raise ForgeError('OPERATION_DOWNLOAD_DEADLINE_REACHED')
            with os.fdopen(fd, 'wb') as out, build_opener(SafeRedirect()).open(Request(url, headers={'User-Agent': 'KAI-Meshy-Forge-Capabilities/1'}), timeout=remaining) as response:
                if not safe_asset_url(response.geturl()):
                    raise ForgeError('OPERATION_ASSET_REDIRECT_DENIED')
                size = 0
                while True:
                    if time.monotonic() >= deadline:
                        raise ForgeError('OPERATION_DOWNLOAD_DEADLINE_REACHED')
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > 512 * 1024 * 1024:
                        raise ForgeError('OPERATION_ASSET_TOO_LARGE')
                    out.write(chunk)
                out.flush(); os.fsync(out.fileno())
            if not size:
                raise ForgeError('OPERATION_ASSET_EMPTY')
            with part.open('rb') as f:
                magic = f.read(4)
            is_zip = magic.startswith(b'PK\x03\x04')
            suffix = '.png' if format in {'thumbnail', 'image', 'base_color', 'metallic', 'normal', 'roughness'} else '.' + format
            if is_zip:
                self._audit_zip(part)
                suffix = '.' + format if format in {'3mf','usdz'} else '.' + format + '.zip'
            elif format in {'thumbnail', 'image', 'base_color', 'metallic', 'normal', 'roughness'}:
                self.forge._decode_image(part)
            elif format in {'glb', 'fbx', 'obj'}:
                from .assets import inspect_model
                inspect_model(part, format_hint=format)
            target = self.forge._workspace_path(folder / (format + '-' + str(texture_index) + ('-'+variant if variant else '') + suffix), strict=False)
            sha = digest(part)
            try:
                final_fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                self.forge._workspace_path(target)
                if digest(target) != sha:
                    raise ForgeError('OPERATION_ASSET_EXISTS_WITHOUT_MATCHING_RECEIPT') from None
            else:
                with os.fdopen(final_fd, 'wb') as out, part.open('rb') as source:
                    shutil.copyfileobj(source, out, 1024 * 1024)
                    out.flush(); os.fsync(out.fileno())
            if digest(target) != sha:
                raise ForgeError('OPERATION_DOWNLOAD_COPY_INTEGRITY_FAILURE')
            role = 'texture' if format in {'base_color', 'metallic', 'normal', 'roughness'} else 'thumbnail' if format == 'thumbnail' else 'preview' if format == 'image' else 'model'
            try:
                asset = self.registry.get('sha256-' + sha)
            except ForgeError as exc:
                if str(exc) != 'ASSET_NOT_FOUND':
                    raise
                asset = self.registry.register(target, role, provenance={'source_id': row['capability_id'], 'task_id': row['task_id'], 'document_state': 'STAGING'})
            with self.forge._db() as c:
                c.execute('INSERT INTO download_receipts VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(job_id,stage,format) DO NOTHING',
                          (job_id, row['stage'], receipt_format, row['task_id'], str(target), sha, size, time.time()))
                registered = c.execute('SELECT * FROM download_receipts WHERE job_id=? AND stage=? AND format=?',(job_id,row['stage'],receipt_format)).fetchone()
                if registered['task_id'] != row['task_id'] or registered['sha256'] != sha or registered['path'] != str(target):
                    raise ForgeError('OPERATION_DOWNLOAD_RECEIPT_CONFLICT')
                self.forge._event(c, job_id, 'OPERATION_ASSET_DOWNLOADED', {'operation_id': operation_id, 'format': format, 'texture_index': texture_index, 'sha256': sha, 'asset_id': asset['id'], 'occurrence_role':role})
            return {'path': str(target), 'sha256': sha, 'bytes': size, 'cached': False,
                    'asset_id': asset['id'], 'format': format, 'texture_index': texture_index,
                    'archive': is_zip, 'scope': 'STRUCTURE_AND_INTEGRITY_ONLY_NOT_GEOMETRY_QA'}
        finally:
            part.unlink(missing_ok=True)

    @staticmethod
    def _audit_zip(path):
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            total = sum(item.file_size for item in infos)
            compressed = max(1, sum(item.compress_size for item in infos))
            if len(infos) > 5000 or total > 1024 * 1024 * 1024 or total / compressed > 500:
                raise ForgeError('OPERATION_ARCHIVE_LIMIT_EXCEEDED')
            seen = set()
            for item in infos:
                name = item.filename.replace('\\', '/')
                if name.startswith('/') or '..' in PurePosixPath(name).parts or re.match(r'^[A-Za-z]:', name) or item.filename in seen or item.flag_bits & 1 or stat.S_ISLNK(item.external_attr >> 16):
                    raise ForgeError('OPERATION_ARCHIVE_UNSAFE_MEMBER')
                seen.add(item.filename)
            if archive.testzip() is not None:
                raise ForgeError('OPERATION_ARCHIVE_CRC_FAILURE')
        return {'members': len(infos), 'uncompressed_bytes': total, 'crc': 'PASS'}

    def extract_operation_archive(self, job_id, operation_id, asset_id):
        row = self._row(job_id, operation_id)
        asset = self.registry.get(asset_id)
        source = self.forge._workspace_path(asset['path'])
        outputs = Path(row['manifest_path']).parent / 'outputs'
        if not source.is_relative_to(outputs):
            raise ForgeError('OPERATION_ARCHIVE_NOT_FROM_THIS_OPERATION')
        audit = self._audit_zip(source)
        destination = self.forge._workspace_path(outputs / ('extracted-' + asset['sha256'][:16]), strict=False)
        destination.mkdir(mode=0o700, exist_ok=True)
        records = []
        with zipfile.ZipFile(source) as archive:
            for item in archive.infolist():
                if item.is_dir():
                    continue
                relative = PurePosixPath(item.filename.replace('\\', '/'))
                # Extract only model/texture/material assets; never executables or code.
                if relative.suffix.lower() not in {'.obj', '.mtl', '.glb', '.gltf', '.fbx', '.stl', '.3mf', '.png', '.jpg', '.jpeg', '.webp', '.exr'}:
                    continue
                target = self.forge._workspace_path(destination.joinpath(*relative.parts), strict=False)
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                data = archive.read(item); sha = hashlib.sha256(data).hexdigest()
                if target.exists():
                    if digest(target) != sha:
                        raise ForgeError('OPERATION_EXTRACT_TARGET_CONFLICT')
                else:
                    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    with os.fdopen(fd, 'wb') as out:
                        out.write(data); out.flush(); os.fsync(out.fileno())
                registered = self.registry.register(target, 'derivative', parent_id=asset_id,
                                                     provenance={'source_id': 'archive-extraction', 'task_id': row['task_id'], 'document_state': 'STAGING'})
                records.append({'asset_id': registered['id'], 'path': str(target), 'sha256': sha})
        with self.forge._db() as c:
            self.forge._event(c, job_id, 'OPERATION_ARCHIVE_EXTRACTED', {'operation_id': operation_id, 'parent_asset_id': asset_id, 'files': len(records), **audit})
        return {'files': records, 'archive': audit, 'executed_code': False}
