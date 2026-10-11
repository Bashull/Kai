from __future__ import annotations
import json,sqlite3,time
from pathlib import Path
from .models import EventEnvelope
from .consumption import at_consumption
REQUIRED={'id','ts','source','type','severity','dedupe_key','payload'}
class WorldBusAdapter:
    """Writes normalized envelopes into the EXISTING WorldBus schema without altering it."""
    def __init__(self,path): self.path=Path(path)
    def connect(self):
        cx=sqlite3.connect(self.path.resolve().as_uri()+'?mode=rw',uri=True,timeout=5,isolation_level=None);cx.execute('PRAGMA busy_timeout=5000');return cx
    def verify_schema(self):
        cx=self.connect()
        try: cols={r[1] for r in cx.execute('PRAGMA table_info(events)')}
        finally: cx.close()
        return {'ok':REQUIRED.issubset(cols),'columns':sorted(cols),'missing':sorted(REQUIRED-cols)}
    def insert(self,e:EventEnvelope)->bool:
        if not self.verify_schema()['ok']: raise RuntimeError('worldbus_schema_mismatch')
        body=json.dumps(at_consumption(e),ensure_ascii=False,separators=(',',':')); typ='nerve.'+e.kind.lower(); sev=2 if e.kind in {'ERROR','DEATH','HURT'} else 0
        level=int(e.provenance.get('level_value',10))
        source='fixture' if level==0 else ('minecraft' if level>=40 and e.source.startswith('minecraft.') else 'minecraft_unverified' if e.source.startswith('minecraft.') else e.source)
        cx=self.connect()
        try:
            cx.execute('BEGIN IMMEDIATE')
            if cx.execute('SELECT 1 FROM events WHERE dedupe_key=? LIMIT 1',(e.event_id,)).fetchone():
                cx.execute('ROLLBACK');return False
            cx.execute('INSERT INTO events(ts,source,type,severity,dedupe_key,payload) VALUES(?,?,?,?,?,?)',(time.time(),source,typ,sev,e.event_id,body));cx.execute('COMMIT');return True
        except Exception:
            try:cx.execute('ROLLBACK')
            except Exception:pass
            raise
        finally: cx.close()
    def get_by_event_id(self,event_id:str):
        if not self.verify_schema()['ok']: raise RuntimeError('worldbus_schema_mismatch')
        cx=self.connect()
        try: row=cx.execute('SELECT id,ts,source,type,severity,dedupe_key,payload FROM events WHERE dedupe_key=? ORDER BY id DESC LIMIT 1',(event_id,)).fetchone()
        finally: cx.close()
        if not row:return None
        return {'id':row[0],'ts':row[1],'source':row[2],'type':row[3],'severity':row[4],'dedupe_key':row[5],'payload':json.loads(row[6])}
