"""Single player observation view; expired/failed scans never prove safety."""
from dataclasses import dataclass,asdict
import math,time
from .consumption import at_consumption
@dataclass
class Track:
    entity_id:str;type_id:str;first_seq:int;last_seq:int;evidence_count:int
    distance:float|None;relative:list|None;location:list|None;unknown:bool
    last_seen_mono:float;state:str='OBSERVED'
class WorldModel:
    def __init__(self,ttl_s=2.0):
        self.session_id=None;self.scope=None;self.tracks={};self.ttl_s=ttl_s;self.scan_state='UNKNOWN'
    def reset(self,session_id):self.session_id=session_id;self.tracks={}
    def snapshot(self):
        now=time.monotonic()
        self.tracks={k:v for k,v in self.tracks.items() if now-v.last_seen_mono<=self.ttl_s}
        return [asdict(t) for t in sorted(self.tracks.values(),key=lambda t:t.distance if t.distance is not None else math.inf)]
    def ingest(self,envelope):
        current=at_consumption(envelope)
        if current['freshness']!='fresh':
            self.scan_state=current['freshness'].upper();return self.snapshot()
        payload=envelope.payload; player=payload.get('player_state') or payload.get('player') or payload
        if not isinstance(player,dict):self.scan_state='ERROR';return self.snapshot()
        scope=(envelope.source,envelope.session_id,str(payload.get('world_id','unknown')),str(player.get('dimension','unknown')),str(player.get('id','unknown')))
        if scope!=self.scope:self.reset(envelope.session_id);self.scope=scope
        scan=payload.get('entity_scan') or player.get('entity_scan') or {}
        if not isinstance(scan,dict):scan={}
        if player.get('entity_scan_error') or scan.get('error') or scan.get('scan_error') or scan.get('state')=='ERROR':
            self.scan_state='ERROR';return self.snapshot()
        ents=scan.get('entities',player.get('entities',payload.get('entities')))
        if not isinstance(ents,list):self.scan_state='UNKNOWN';return self.snapshot()
        truncated=bool(scan.get('truncated',player.get('entities_truncated',False)))
        self.scan_state='TRUNCATED' if truncated else ('OBSERVED' if ents else 'EMPTY_OBSERVED')
        seen=set();now=time.monotonic()
        for x in ents[:256]:
            if not isinstance(x,dict) or not isinstance(x.get('id'),str) or not x['id']:continue
            eid=x['id'];seen.add(eid);old=self.tracks.get(eid);tid=str(x.get('typeId') or x.get('type_id') or 'unknown')
            dist=x.get('distance');dist=dist if type(dist) in (int,float) and math.isfinite(dist) and dist>=0 else None
            self.tracks[eid]=Track(eid,tid,old.first_seq if old else envelope.source_seq,envelope.source_seq,(old.evidence_count+1 if old else 1),dist,x.get('relative'),x.get('location'),not tid.startswith('minecraft:'),now)
        for eid in list(self.tracks):
            if eid not in seen:
                if truncated:self.tracks[eid].state='NOT_SEEN_IN_PARTIAL_SCAN'
                else:del self.tracks[eid]
        return self.snapshot()
