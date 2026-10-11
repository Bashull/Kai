from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum, IntEnum
from typing import Any, Optional
import hashlib, json, time

class Freshness(str, Enum):
    FRESH="fresh"; STALE="stale"; UNKNOWN="unknown"; REPLAY="replay"

class ProvenanceLevel(IntEnum):
    FIXTURE=0
    UNVERIFIED=10
    PROCESS_BOUND=20
    TRANSPORT_BOUND=30
    ENGINE_BOUNDARY=40

@dataclass(frozen=True)
class ProvenanceEvidence:
    level: ProvenanceLevel
    collector: str
    transport: str
    evidence: dict[str, Any]
    def to_dict(self):
        return {"level":self.level.name.lower(),"level_value":int(self.level),
                "collector":self.collector,"transport":self.transport,
                "evidence":self.evidence}

@dataclass
class ParsedObservation:
    source: str
    kind: str
    payload: dict[str, Any]
    session_id: Optional[str]=None
    source_seq: Optional[int]=None
    observed_wall_ms: Optional[float]=None
    observed_tick: Optional[int]=None
    claimed_provenance: dict[str,Any]|None=None

@dataclass
class EventEnvelope:
    event_id:str; schema:str; source:str; kind:str
    session_id:Optional[str]; source_seq:Optional[int]
    observed_wall_ms:Optional[float]; observed_tick:Optional[int]
    received_wall_ms:float; published_wall_ms:float; consumed_wall_ms:float
    source_age_ms:Optional[float]; publish_delay_ms:Optional[float]
    publication_age_ms:Optional[float]; detection_age_ms:Optional[float]
    effective_age_ms:Optional[float]
    freshness:Freshness; fresh_reason:str
    provenance:dict[str,Any]; actuation_eligible:bool
    payload:dict[str,Any]
    receipt_monotonic_ms:float|None=None
    clock_instance:str|None=None
    max_age_ms:float=750.0
    def to_dict(self):
        d=asdict(self); d['freshness']=self.freshness.value; return d

def now_ms()->float: return time.time()*1000.0

def stable_event_id(source,session_id,seq,kind,payload):
    raw=json.dumps([source,session_id,seq,kind,payload],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
    return hashlib.sha256(raw).hexdigest()[:32]
