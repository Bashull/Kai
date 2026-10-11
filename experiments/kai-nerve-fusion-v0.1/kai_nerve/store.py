from __future__ import annotations
import json,sqlite3
from pathlib import Path
SCHEMA="""PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS events(
 id INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT NOT NULL UNIQUE,
 received_wall_ms REAL NOT NULL,source TEXT NOT NULL,kind TEXT NOT NULL,
 session_id TEXT,source_seq INTEGER,observed_wall_ms REAL,effective_age_ms REAL,
 freshness TEXT NOT NULL,allow_actuation INTEGER NOT NULL,payload TEXT NOT NULL,provenance TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_events_source_session_seq ON events(source,session_id,source_seq);
CREATE UNIQUE INDEX IF NOT EXISTS uq_events_source_session_seq_kind
 ON events(source,session_id,source_seq,kind)
 WHERE session_id IS NOT NULL AND source_seq IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_events_received ON events(received_wall_ms);"""
class EventStore:
 def __init__(self,path):
  self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
  with self.connect() as cx:cx.executescript(SCHEMA)
 def connect(self):
  cx=sqlite3.connect(self.path,timeout=5);cx.execute("PRAGMA synchronous=NORMAL");return cx
 def insert(self,e):
  with self.connect() as cx:
   try:
    cx.execute("""INSERT INTO events(event_id,received_wall_ms,source,kind,session_id,source_seq,
     observed_wall_ms,effective_age_ms,freshness,allow_actuation,payload,provenance)
     VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",(e.event_id,e.received_wall_ms,e.source,e.kind,e.session_id,
     e.source_seq,e.observed_wall_ms,e.effective_age_ms,e.freshness.value,int(e.allow_actuation),
     json.dumps(e.payload,ensure_ascii=False,separators=(",",":")),
     json.dumps(e.provenance,ensure_ascii=False,separators=(",",":"))));return True
   except sqlite3.IntegrityError:return False
