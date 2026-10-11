from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Optional
import hashlib, json, time

class Freshness(str, Enum):
    FRESH="fresh"; STALE="stale"; UNKNOWN="unknown"; REPLAY="replay"

@dataclass
class ParsedObservation:
    source:str; kind:str; payload:dict[str,Any]
    session_id:Optional[str]=None; source_seq:Optional[int]=None
    observed_wall_ms:Optional[float]=None; observed_tick:Optional[int]=None
    provenance:dict[str,Any]|None=None

@dataclass
class EventEnvelope:
    event_id:str; schema:str; source:str; kind:str
    session_id:Optional[str]; source_seq:Optional[int]
    observed_wall_ms:Optional[float]; observed_tick:Optional[int]
    received_wall_ms:float; published_wall_ms:float
    source_age_ms:Optional[float]; transport_age_ms:Optional[float]
    effective_age_ms:Optional[float]; freshness:Freshness
    fresh_reason:str; allow_actuation:bool
    payload:dict[str,Any]; provenance:dict[str,Any]
    def to_dict(self):
        d=asdict(self); d["freshness"]=self.freshness.value; return d

def now_ms(): return time.time()*1000.0

def stable_event_id(source,session_id,seq,kind,payload):
    raw=json.dumps([source,session_id,seq,kind,payload],ensure_ascii=False,
        sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(raw).hexdigest()[:32]
