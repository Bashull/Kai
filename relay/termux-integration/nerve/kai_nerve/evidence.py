"""Bounded RAW CAS and independent occurrences; full returns a closed gate."""
import hashlib,json,sqlite3,time
from pathlib import Path
from contextlib import closing
class EvidenceStore:
    def __init__(self,path,max_bytes=64*1024*1024,max_occurrences=50000):
        self.path=Path(path);self.max_bytes=max_bytes;self.max_occurrences=max_occurrences
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with closing(sqlite3.connect(self.path)) as c:
            c.executescript("CREATE TABLE IF NOT EXISTS blobs(sha TEXT PRIMARY KEY,data BLOB NOT NULL); CREATE TABLE IF NOT EXISTS occurrences(id INTEGER PRIMARY KEY,sha TEXT NOT NULL,received_ms REAL NOT NULL,metadata TEXT NOT NULL);")
    def add(self,raw,metadata):
        if type(raw) is not bytes or len(raw)>65536:raise ValueError('raw_size_or_type')
        h=hashlib.sha256(raw).hexdigest()
        with closing(sqlite3.connect(self.path,timeout=5,isolation_level=None)) as c:
            c.execute('BEGIN IMMEDIATE')
            exists=c.execute('SELECT 1 FROM blobs WHERE sha=?',(h,)).fetchone()
            size=c.execute('SELECT COALESCE(SUM(length(data)),0) FROM blobs').fetchone()[0]
            count=c.execute('SELECT count(*) FROM occurrences').fetchone()[0]
            if count>=self.max_occurrences or size+(0 if exists else len(raw))>self.max_bytes:
                c.rollback();raise RuntimeError('evidence_capacity_reached')
            c.execute('INSERT OR IGNORE INTO blobs VALUES(?,?)',(h,raw))
            ident=c.execute('INSERT INTO occurrences(sha,received_ms,metadata) VALUES(?,?,?)',(h,time.time()*1000,json.dumps(metadata,allow_nan=False))).lastrowid
            c.commit();return {'sha256':h,'occurrence_id':ident,'bytes':len(raw)}
