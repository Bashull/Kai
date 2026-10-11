from __future__ import annotations
import time, json
from .evidence import EvidenceStore
from .worldmodel import WorldModel
from .parsers import parse_line
from .models import EventEnvelope,Freshness
from pathlib import Path
from .collector_logcat import iterate
from .freshness import ReplayLedger
from .normalize import Normalizer
from .store import EventStore
from .worldbus import WorldBusAdapter

class IngestPipeline:
    """Sensor ingress only. It persists evidence and never calls a physical actuator."""
    def __init__(self,*,nerve_db:str|Path,replay_db:str|Path,worldbus_db:str|Path,max_age_ms:float=750.0):
        self.evidence=EvidenceStore(str(nerve_db)+'.raw.sqlite3')
        self.model=WorldModel()
        self.replay=ReplayLedger(replay_db)
        self.normalizer=Normalizer(self.replay,max_age_ms=max_age_ms)
        self.store=EventStore(nerve_db)
        self.worldbus=WorldBusAdapter(worldbus_db)
    def drain_pending(self):
        count=0
        for d in self.store.pending():
            d['freshness']=Freshness(d['freshness']); e=EventEnvelope(**d)
            e.actuation_eligible=False
            self.worldbus.insert(e)
            if self.worldbus.get_by_event_id(e.event_id):self.store.mark_delivered(e.event_id);count+=1
        return count
    def process_line(self,raw,evidence,received_wall_ms):
        self.drain_pending()
        proof=self.evidence.add(raw,{'representation':'collector_raw','collector':evidence.collector,'transport':evidence.transport})
        obs=parse_line(raw.decode('utf-8',errors='replace'))
        if obs is None:return {'parse_error':True,'raw':proof}
        return self.process(obs,evidence,received_wall_ms,raw_proof=proof)
    def process(self,obs,evidence,received_wall_ms:float,raw_proof=None):
        if raw_proof is None:
            raw_proof=self.evidence.add(json.dumps(obs.payload,allow_nan=False).encode(),{'representation':'parsed_projection_not_raw'})
        # A parsed projection never manufactures collector evidence.
        evidence=type(evidence)(evidence.level,evidence.collector,evidence.transport,{**evidence.evidence,'raw':raw_proof})
        now=time.time()*1000.0
        env=self.normalizer.normalize(obs,evidence=evidence,received_wall_ms=received_wall_ms,published_wall_ms=now,consumed_wall_ms=now)
        if env.freshness.value=='replay':
            return {'event':env,'internal_inserted':False,'worldbus_inserted':False,'worldbus_readback':None,'tracks':self.model.snapshot(),'scan_state':'REPLAY','raw':raw_proof}
        internal=self.store.insert(env)
        worldbus=self.worldbus.insert(env)
        self.store.mark_delivered(env.event_id)
        proof=self.worldbus.get_by_event_id(env.event_id)
        tracks=self.model.ingest(env)
        return {'tracks':tracks,'scan_state':self.model.scan_state,'raw':raw_proof,'event':env,'internal_inserted':internal,'worldbus_inserted':worldbus,'worldbus_readback':proof}
    def close(self): self.replay.close()

def collect_logcat(*,serial:str,nerve_db:str|Path,replay_db:str|Path,worldbus_db:str|Path,expected_challenge:str,max_age_ms:float=750.0,once:bool=False):
    pipe=IngestPipeline(nerve_db=nerve_db,replay_db=replay_db,worldbus_db=worldbus_db,max_age_ms=max_age_ms)
    try:
        while True:
            try:
                for raw,evidence,received in iterate(serial,expected_challenge=expected_challenge,max_wait_s=30 if once else None):
                    result=pipe.process_line(raw,evidence,received)
                    yield result
                    if once and result.get('event') and result['worldbus_readback']:
                        return
                if once:
                    yield {'collector_error':'timeout_or_eof','deadline_s':30};return
                time.sleep(2)
            except KeyboardInterrupt:
                return
            except Exception as exc:
                yield {'collector_error':type(exc).__name__,'message':str(exc)[:240]}
                if once:return
                time.sleep(1.0)
    finally:
        pipe.close()
