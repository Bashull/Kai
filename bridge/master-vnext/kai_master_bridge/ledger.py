"""SQLite receipts, crash-safe claim and offline local-human approvals."""
from __future__ import annotations
import json
from contextlib import contextmanager
import os
import sqlite3
import time
from pathlib import Path

class LedgerError(RuntimeError):
    pass

class Ledger:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if os.name != 'nt':
            self.path.parent.chmod(0o700)
        with self.open() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS actions (
                request_id TEXT PRIMARY KEY, digest TEXT NOT NULL, status TEXT NOT NULL,
                receipt_json TEXT, created_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS approvals (
                request_id TEXT PRIMARY KEY, digest TEXT NOT NULL,
                expires INTEGER NOT NULL, used INTEGER NOT NULL DEFAULT 0,
                actor TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS audit (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT, at INTEGER NOT NULL,
                request_id TEXT, capability TEXT, event TEXT NOT NULL);
            ''')

    @contextmanager
    def open(self):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        try:
            if os.name != 'nt':
                self.path.chmod(0o600)
            db.execute('PRAGMA busy_timeout=10000')
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('PRAGMA synchronous=FULL')
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def add_approval(self, request_id, digest, actor='local-owner', ttl=120):
        if not isinstance(digest, str) or len(digest) != 64 or not all(c in '0123456789abcdef' for c in digest):
            raise LedgerError('INVALID_DIGEST')
        if not isinstance(actor, str) or actor != 'local-owner' or not 1 <= ttl <= 300:
            raise LedgerError('INVALID_APPROVAL')
        with self.open() as db:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT status FROM actions WHERE request_id=?', (request_id,)).fetchone()
            if existing:
                db.rollback()
                raise LedgerError('REQUEST_ALREADY_CLAIMED')
            db.execute('INSERT INTO approvals (request_id,digest,expires,used,actor) VALUES(?,?,?,?,?) '
                       'ON CONFLICT(request_id) DO UPDATE SET digest=excluded.digest,expires=excluded.expires,used=0,actor=excluded.actor',
                       (request_id, digest, int(time.time())+ttl, 0, actor))
            db.execute('INSERT INTO audit (at,request_id,event) VALUES(?,?,?)',
                       (int(time.time()), request_id, 'OWNER_APPROVED'))
            db.commit()

    def claim(self, action, needs_approval=False):
        """Return (NEW, None), (EXISTING, receipt), or (NEEDS_APPROVAL, None).
        Never reexecute pending claims after restart or concurrent calls."""
        digest = action.digest()
        with self.open() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT digest,status,receipt_json FROM actions WHERE request_id=?',
                             (action.request_id,)).fetchone()
            if row:
                db.commit()
                if row[0] != digest:
                    raise LedgerError('REQUEST_ID_CONFLICT')
                return 'EXISTING', json.loads(row[2]) if row[2] else {'status': 'IN_PROGRESS_OR_INTERRUPTED'}
            if needs_approval:
                approval = db.execute('SELECT digest,expires,used FROM approvals WHERE request_id=?',
                                      (action.request_id,)).fetchone()
                if not approval or approval[0] != digest or approval[1] < int(time.time()) or approval[2]:
                    db.commit()
                    return 'NEEDS_APPROVAL', None
                db.execute('UPDATE approvals SET used=1 WHERE request_id=?', (action.request_id,))
            db.execute('INSERT INTO actions(request_id,digest,status,created_at) VALUES(?,?,?,?)',
                       (action.request_id,digest,'RUNNING',int(time.time())))
            db.execute('INSERT INTO audit(at,request_id,capability,event) VALUES(?,?,?,?)',
                       (int(time.time()),action.request_id,action.capability,'CLAIMED'))
            db.commit()
            return 'NEW', None

    def finish(self, action, rec):
        with self.open() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE actions SET status=?,receipt_json=? WHERE request_id=? AND digest=?',
                (rec['status'], json.dumps(rec, ensure_ascii=False, separators=(',',':')),
                 action.request_id,action.digest()))
            db.execute('INSERT INTO audit(at,request_id,capability,event) VALUES(?,?,?,?)',
                       (int(time.time()), action.request_id, action.capability, rec['status']))
            db.commit()
