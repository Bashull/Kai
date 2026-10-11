from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
import sqlite3, threading
from .models import Freshness

@dataclass(frozen=True)
class FreshnessDecision:
    freshness:Freshness
    reason:str
    source_age_ms:float|None
    publish_delay_ms:float|None
    publication_age_ms:float|None
    detection_age_ms:float|None
    effective_age_ms:float|None

class ReplayLedger:
    """Persistent monotonic sequence memory. Survives collector restarts."""
    def __init__(self,path: str|Path|None=None):
        self.path=':memory:' if path is None else str(path)
        self.cx=sqlite3.connect(self.path,timeout=5,check_same_thread=False, isolation_level=None)
        self.lock=threading.RLock()
        self._closed=False
        self.cx.execute('CREATE TABLE IF NOT EXISTS seq(source TEXT, session TEXT, last_seq INTEGER, PRIMARY KEY(source,session))')
    def classify_and_advance(self,source:str,session:str,seq:int)->bool:
        if type(seq) is not int or not 0 <= seq <= 9007199254740991:
            return False
        with self.lock:
            try:
                self.cx.execute('BEGIN IMMEDIATE')
                row=self.cx.execute('SELECT last_seq FROM seq WHERE source=? AND session=?',(source,session)).fetchone()
                if row is not None and seq <= row[0]:
                    self.cx.execute('ROLLBACK'); return False
                self.cx.execute('INSERT INTO seq VALUES(?,?,?) ON CONFLICT(source,session) DO UPDATE SET last_seq=excluded.last_seq',(source,session,seq))
                self.cx.execute('COMMIT'); return True
            except Exception:
                if self.cx.in_transaction: self.cx.execute('ROLLBACK')
                raise
    def close(self):
        if not getattr(self,'_closed',True):
            self.cx.close(); self._closed=True
    def __del__(self):
        try:self.close()
        except Exception:pass

def _num(name,v):
    if v is None: return None
    if isinstance(v,bool) or not isinstance(v,(int,float)): raise ValueError(f'{name}_not_numeric')
    try: x=float(v)
    except (TypeError,ValueError): raise ValueError(f'{name}_not_numeric')
    if not isfinite(x): raise ValueError(f'{name}_not_finite')
    return x

def temporal_decision(*,session_id:str|None,seq:int|None,source:str,replay:ReplayLedger,
                      observed_wall_ms:float|None,received_wall_ms:float,published_wall_ms:float,
                      consumed_wall_ms:float,frame_age_at_publish_ms:float|None=None,
                      detection_wall_ms:float|None=None,process_ok:bool=True,max_age_ms:float=750.0,
                      max_future_skew_ms:float=250.0)->FreshnessDecision:
    if not process_ok:
        return FreshnessDecision(Freshness.STALE,'source_not_ok',None,None,None,None,None)
    if not session_id:
        return FreshnessDecision(Freshness.UNKNOWN,'missing_session_id',None,None,None,None,None)
    if type(seq) is not int or not 0 <= seq <= 9007199254740991:
        return FreshnessDecision(Freshness.UNKNOWN,'missing_source_seq',None,None,None,None,None)
    try:
        received=_num('received_wall_ms',received_wall_ms); published=_num('published_wall_ms',published_wall_ms); consumed=_num('consumed_wall_ms',consumed_wall_ms)
        observed=_num('observed_wall_ms',observed_wall_ms); frame_age=_num('frame_age_at_publish_ms',frame_age_at_publish_ms); detected=_num('detection_wall_ms',detection_wall_ms)
    except ValueError as e:
        return FreshnessDecision(Freshness.UNKNOWN,str(e),None,None,None,None,None)
    if any(x is None for x in (received,published,consumed)):
        return FreshnessDecision(Freshness.UNKNOWN,'missing_collector_time',None,None,None,None,None)
    if published < received: return FreshnessDecision(Freshness.UNKNOWN,'published_before_received',None,None,None,None,None)
    if consumed < published: return FreshnessDecision(Freshness.UNKNOWN,'consumed_before_published',None,None,None,None,None)
    if observed is not None and observed > received + max_future_skew_ms:
        return FreshnessDecision(Freshness.UNKNOWN,'observed_in_future',None,None,None,None,None)
    if detected is not None and detected > consumed + max_future_skew_ms:
        return FreshnessDecision(Freshness.UNKNOWN,'detection_in_future',None,None,None,None,None)
    if frame_age is not None and frame_age < 0:
        return FreshnessDecision(Freshness.UNKNOWN,'negative_frame_age',None,None,None,None,None)
    pub_delay=published-received; pub_age=consumed-published
    source_age=None
    paths=[]
    if observed is not None:
        source_age=received-observed
        if source_age < 0: return FreshnessDecision(Freshness.UNKNOWN,'negative_source_age',None,pub_delay,pub_age,None,None)
        paths.append(source_age+pub_delay+pub_age)
    if frame_age is not None:
        paths.append(frame_age+pub_age)
    det_age=None
    if detected is not None:
        det_age=consumed-detected
        if det_age<0: return FreshnessDecision(Freshness.UNKNOWN,'negative_detection_age',source_age,pub_delay,pub_age,None,None)
        paths.append(det_age)
    if not paths:
        return FreshnessDecision(Freshness.UNKNOWN,'missing_origin_age',source_age,pub_delay,pub_age,det_age,None)
    effective=max(paths)
    if not replay.classify_and_advance(source,session_id,seq):
        return FreshnessDecision(Freshness.REPLAY,'non_monotonic_sequence',source_age,pub_delay,pub_age,det_age,effective)
    if effective>max_age_ms:
        return FreshnessDecision(Freshness.STALE,f'effective_age>{max_age_ms:g}ms',source_age,pub_delay,pub_age,det_age,effective)
    return FreshnessDecision(Freshness.FRESH,'all_available_age_paths_within_budget',source_age,pub_delay,pub_age,det_age,effective)
