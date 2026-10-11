from __future__ import annotations
import json,sqlite3
from pathlib import Path
from .models import EventEnvelope
SCHEMA="""
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS events(
 id INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT NOT NULL UNIQUE,received_wall_ms REAL NOT NULL,
 source TEXT NOT NULL,kind TEXT NOT NULL,session_id TEXT,source_seq INTEGER,effective_age_ms REAL,
 freshness TEXT NOT NULL,provenance_level INTEGER NOT NULL,actuation_eligible INTEGER NOT NULL,
 envelope TEXT NOT NULL);
DROP INDEX IF EXISTS uq_source_session_seq_kind;
CREATE TABLE IF NOT EXISTS delivered(event_id TEXT PRIMARY KEY);
"""
class EventStore:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        cx=self.connect()
        try:cx.executescript(SCHEMA);cx.commit()
        finally:cx.close()
    def connect(self):
        cx=sqlite3.connect(self.path,timeout=5);cx.execute('PRAGMA synchronous=NORMAL');return cx
    def insert(self,e:EventEnvelope)->bool:
        plev=int((e.provenance or {}).get('level_value',0)); raw=json.dumps(e.to_dict(),ensure_ascii=False,separators=(',',':'))
        cx=self.connect()
        try:
            try:
                cx.execute('INSERT INTO events(event_id,received_wall_ms,source,kind,session_id,source_seq,effective_age_ms,freshness,provenance_level,actuation_eligible,envelope) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                  (e.event_id,e.received_wall_ms,e.source,e.kind,e.session_id,e.source_seq,e.effective_age_ms,e.freshness.value,plev,int(e.actuation_eligible),raw));cx.commit();return True
            except sqlite3.IntegrityError:return False
        finally:cx.close()
    def recent(self,limit=20):
        cx=self.connect()
        try:rows=cx.execute('SELECT envelope FROM events ORDER BY id DESC LIMIT ?',(max(1,min(int(limit),500)),)).fetchall()
        finally:cx.close()
        from .consumption import at_consumption
        return [at_consumption(json.loads(r[0])) for r in rows]

    def pending(self,limit=100):
        cx=self.connect()
        try:return [json.loads(r[0]) for r in cx.execute('SELECT envelope FROM events WHERE event_id NOT IN (SELECT event_id FROM delivered) ORDER BY id LIMIT ?',(limit,))]
        finally:cx.close()
    def mark_delivered(self,event_id):
        cx=self.connect()
        try:cx.execute('INSERT OR IGNORE INTO delivered VALUES(?)',(event_id,));cx.commit()
        finally:cx.close()
