"""SQLite-consistent backup of the single Forge state, restored only in isolation."""
from pathlib import Path
from contextlib import closing
import os
import sqlite3
import tempfile
import json
from .core import ForgeError, digest


def snapshot(forge):
    folder = forge.root / 'backups'
    if folder.is_symlink() or not folder.resolve().is_relative_to(forge.root):
        raise ForgeError('BACKUP_SYMLINK_DENIED')
    folder.mkdir(mode=0o700, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='forge-', suffix='.sqlite3', dir=folder)
    os.close(fd)
    target = Path(name)
    try:
        with closing(sqlite3.connect(forge.db)) as source, closing(sqlite3.connect(target)) as destination:
            source.backup(destination)
            if destination.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ForgeError('BACKUP_INTEGRITY_FAILED')
        os.chmod(target, 0o600)
        return {'path': str(target), 'sha256': digest(target), 'bytes': target.stat().st_size,
                'scope': 'CONSISTENT_STATE_COPY', 'source_runtime_unchanged': True}
    except Exception:
        target.unlink(missing_ok=True)
        raise


def verify_restore(forge, backup):
    raw = Path(backup).expanduser()
    if raw.is_symlink() or (forge.root / 'backups').is_symlink():
        raise ForgeError('BACKUP_SYMLINK_DENIED')
    source = raw.resolve(strict=True)
    if not source.is_relative_to((forge.root / 'backups').resolve()):
        raise ForgeError('BACKUP_OUTSIDE_RUNTIME')
    with tempfile.TemporaryDirectory(prefix='kai-restore-') as temporary:
        target = Path(temporary) / 'restored.sqlite3'
        with closing(sqlite3.connect(source)) as db, closing(sqlite3.connect(target)) as restored:
            db.backup(restored)
            check = restored.execute('PRAGMA integrity_check').fetchone()[0]
            jobs = restored.execute('SELECT count(*) FROM jobs').fetchone()[0]
            stages = restored.execute('SELECT count(*) FROM stages').fetchone()[0]
            tables = [x[0] for x in restored.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        if check != 'ok':
            raise ForgeError('RESTORE_INTEGRITY_FAILED')
        return {'restore_integrity': check, 'jobs': jobs, 'stages': stages, 'tables': tables,
                'backup_sha256': digest(source), 'live_database_replaced': False,
                'scope': 'SQLITE_STATE_ONLY_ASSET_RESTORE_SEPARATE'}


def recovery_files(forge, backup):
    """Resolve all immutable file occurrences referenced by a consistent DB copy.

    Generic operations can reuse a registry identity at another private path.
    Registry rows alone therefore do not cover their request media or outputs.
    The returned paths are confined to this workspace and contain no CLI store.
    This inventories a backup; it neither moves nor restores live files.
    """
    source = forge._workspace_path(backup)
    if not source.is_relative_to(forge.root / 'backups'):
        raise ForgeError('BACKUP_OUTSIDE_RUNTIME')
    files = {}

    def add(path, sha, purpose):
        target = forge._workspace_path(path)
        if not target.is_file() or digest(target) != sha:
            raise ForgeError('RECOVERY_REFERENCED_FILE_CHANGED')
        relative = target.relative_to(forge.root).as_posix()
        if relative in files and files[relative]['sha256'] != sha:
            raise ForgeError('RECOVERY_REFERENCED_FILE_HASH_CONFLICT')
        files.setdefault(relative, {'path': relative, 'sha256': sha,
                                     'bytes': target.stat().st_size, 'purposes': []})
        if purpose not in files[relative]['purposes']:
            files[relative]['purposes'].append(purpose)

    add(source, digest(source), 'consistent_sqlite_snapshot')
    with closing(sqlite3.connect(source)) as db:
        db.row_factory = sqlite3.Row
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ForgeError('BACKUP_INTEGRITY_FAILED')
        for row in db.execute('SELECT source,source_sha FROM jobs'):
            add(row['source'], row['source_sha'], 'job_source')
        tables = {r['name'] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'assets' in tables:
            for row in db.execute('SELECT path,sha256 FROM assets'):
                add(row['path'], row['sha256'], 'registry_asset')
        for row in db.execute('SELECT path,sha256 FROM download_receipts'):
            add(row['path'], row['sha256'], 'download_occurrence')
        columns = {r['name'] for r in db.execute('PRAGMA table_info(stages)')}
        if 'manifest_path' in columns:
            for row in db.execute('SELECT manifest_path,manifest_sha FROM stages WHERE manifest_path IS NOT NULL'):
                add(row['manifest_path'], row['manifest_sha'], 'operation_manifest')
                manifest = forge._workspace_path(row['manifest_path'])
                if manifest.stat().st_size > 1024 * 1024:
                    raise ForgeError('RECOVERY_OPERATION_MANIFEST_TOO_LARGE')
                try:
                    data = json.loads(manifest.read_text())
                except (ValueError, UnicodeError):
                    raise ForgeError('RECOVERY_OPERATION_MANIFEST_INVALID') from None

                def walk(value, depth=0):
                    if depth > 16:
                        raise ForgeError('RECOVERY_OPERATION_MANIFEST_TOO_DEEP')
                    if isinstance(value, dict):
                        if set(value) == {'reference'}:
                            ref = value['reference']
                            if not isinstance(ref, dict) or not all(k in ref for k in ('local_copy', 'sha256')):
                                raise ForgeError('RECOVERY_OPERATION_REFERENCE_INVALID')
                            add(ref['local_copy'], ref['sha256'], 'operation_media_occurrence')
                        else:
                            for item in value.values():
                                walk(item, depth + 1)
                    elif isinstance(value, list):
                        for item in value:
                            walk(item, depth + 1)
                walk(data)
    return {'schema': 'kai.meshy.recovery-files/1', 'files': sorted(files.values(), key=lambda r: r['path']),
            'scope': 'DATABASE_AND_ALL_REFERENCED_FILE_OCCURRENCES',
            'cross_node_path_relocation': 'REQUIRES_EXPLICIT_MIGRATION; ORIGINAL_MANIFESTS_IMMUTABLE',
            'cli_credentials_included': False}
