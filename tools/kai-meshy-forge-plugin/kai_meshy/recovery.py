"""SQLite-consistent backup of the single Forge state, restored only in isolation."""
from pathlib import Path
from contextlib import closing
import os
import sqlite3
import tempfile
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
