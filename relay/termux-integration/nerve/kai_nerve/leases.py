from __future__ import annotations
import sqlite3,time,secrets
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Lease:
    role:str;owner:str;token:str;expires_wall_ms:float
    @property
    def expired(self):return time.time()*1000.0>=self.expires_wall_ms

class LeaseStore:
    """Small SQLite lease store. One live owner per physical/single-owner role."""
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        cx=self._cx();cx.execute('CREATE TABLE IF NOT EXISTS leases(role TEXT PRIMARY KEY,owner TEXT NOT NULL,token TEXT NOT NULL,expires_wall_ms REAL NOT NULL,updated_wall_ms REAL NOT NULL)');cx.commit();cx.close()
    def _cx(self):
        cx=sqlite3.connect(self.path,timeout=5,isolation_level=None);cx.execute('PRAGMA busy_timeout=5000');return cx
    def acquire(self,role,owner,ttl_ms=2000,now_ms=None):
        now=time.time()*1000 if now_ms is None else float(now_ms);token=secrets.token_urlsafe(18);exp=now+float(ttl_ms)
        cx=self._cx()
        try:
            cx.execute('BEGIN IMMEDIATE');row=cx.execute('SELECT owner,token,expires_wall_ms FROM leases WHERE role=?',(role,)).fetchone()
            if row and float(row[2])>now and row[0]!=owner:
                cx.execute('ROLLBACK');return None
            cx.execute('INSERT INTO leases(role,owner,token,expires_wall_ms,updated_wall_ms) VALUES(?,?,?,?,?) ON CONFLICT(role) DO UPDATE SET owner=excluded.owner,token=excluded.token,expires_wall_ms=excluded.expires_wall_ms,updated_wall_ms=excluded.updated_wall_ms',(role,owner,token,exp,now));cx.execute('COMMIT');return Lease(role,owner,token,exp)
        except Exception:
            try:cx.execute('ROLLBACK')
            except Exception:pass
            raise
        finally:cx.close()
    def renew(self,lease:Lease,ttl_ms=2000,now_ms=None):
        now=time.time()*1000 if now_ms is None else float(now_ms);exp=now+float(ttl_ms);cx=self._cx()
        try:
            cur=cx.execute('UPDATE leases SET expires_wall_ms=?,updated_wall_ms=? WHERE role=? AND owner=? AND token=? AND expires_wall_ms>?',(exp,now,lease.role,lease.owner,lease.token,now));cx.commit();return Lease(lease.role,lease.owner,lease.token,exp) if cur.rowcount==1 else None
        finally:cx.close()
    def valid(self,lease:Lease,now_ms=None):
        now=time.time()*1000 if now_ms is None else float(now_ms);cx=self._cx()
        try:row=cx.execute('SELECT expires_wall_ms FROM leases WHERE role=? AND owner=? AND token=?',(lease.role,lease.owner,lease.token)).fetchone();return bool(row and float(row[0])>now)
        finally:cx.close()
