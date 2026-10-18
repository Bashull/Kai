"""Asset lineage stored in the Forge database, without a second ledger."""
import json
from pathlib import Path
import time
from .core import ForgeError, digest


class AssetRegistry:
    def __init__(self, forge):
        self.forge = forge
        with forge._db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS assets (id TEXT PRIMARY KEY, path TEXT NOT NULL, sha256 TEXT NOT NULL, parent_id TEXT, role TEXT NOT NULL, provenance TEXT NOT NULL, created REAL NOT NULL)')

    def _path(self, value):
        original = Path(value).expanduser()
        if original.is_symlink():
            raise ForgeError('SYMLINK_ASSET_DENIED')
        p = original.resolve(strict=True)
        if not p.is_relative_to(self.forge.root) or not p.is_file():
            raise ForgeError('ASSET_OUTSIDE_WORKSPACE')
        return p

    def get(self, asset_id):
        with self.forge._db() as db:
            row = db.execute('SELECT * FROM assets WHERE id=?', (asset_id,)).fetchone()
        if row is None:
            raise ForgeError('ASSET_NOT_FOUND')
        result = dict(row)
        result['provenance'] = json.loads(result['provenance'])
        p = self._path(result['path'])
        result['integrity_verified'] = digest(p) == result['sha256']
        if not result['integrity_verified']:
            raise ForgeError('IMMUTABLE_ASSET_CHANGED')
        return result

    def register(self, path, role, parent_id=None, provenance=None):
        if role not in ('reference', 'preview', 'model', 'texture', 'thumbnail', 'derivative', 'evidence'):
            raise ForgeError('INVALID_ASSET_ROLE')
        p = self._path(path)
        sha = digest(p)
        asset_id = 'sha256-' + sha
        if parent_id == asset_id:
            raise ForgeError('SELF_PARENT_DENIED')
        if parent_id:
            self.get(parent_id)
        # Provenance is deliberately narrow: no arbitrary private metadata payloads.
        provenance = provenance or {}
        allowed = {'source_id', 'author', 'license', 'task_id', 'document_state'}
        if not isinstance(provenance, dict) or set(provenance) - allowed:
            raise ForgeError('INVALID_PROVENANCE_FIELDS')
        if any(not isinstance(v, str) or len(v) > 500 for v in provenance.values()):
            raise ForgeError('INVALID_PROVENANCE_VALUES')
        from .core import public_json
        if public_json(provenance) != provenance:
            raise ForgeError('SECRET_OR_REMOTE_REFERENCE_DENIED')
        with self.forge._db() as db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT * FROM assets WHERE id=?', (asset_id,)).fetchone()
            if old:
                if old['parent_id'] != parent_id or old['role'] != role:
                    raise ForgeError('ASSET_LINEAGE_CONFLICT')
            else:
                db.execute('INSERT INTO assets VALUES (?,?,?,?,?,?,?)', (asset_id, str(p), sha, parent_id, role, json.dumps(provenance, sort_keys=True), time.time()))
        return self.get(asset_id)

    def list(self, limit=100):
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise ForgeError('INVALID_LIMIT')
        with self.forge._db() as db:
            rows = db.execute('SELECT id FROM assets ORDER BY created,id LIMIT ?', (limit,)).fetchall()
        return [self.get(row['id']) for row in rows]

    def inspect_reference(self, path):
        p = self._path(path)
        if p.stat().st_size > 20 * 1024 * 1024:
            raise ForgeError('REFERENCE_TOO_LARGE')
        from PIL import Image
        with Image.open(p) as image:
            image.verify()
        with Image.open(p) as image:
            return {'file': str(p), 'sha256': digest(p), 'bytes': p.stat().st_size,
                    'format': image.format, 'width': image.width, 'height': image.height,
                    'mode': image.mode, 'scope': 'IMAGE_STRUCTURE_ONLY',
                    'visual_qa': 'HUMAN_REVIEW_REQUIRED', 'source_modified': False}
