from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from .models import Freshness

@dataclass
class FreshnessDecision:
    freshness:Freshness; reason:str; effective_age_ms:Optional[float]; allow_actuation:bool

class SequenceTracker:
    def __init__(self): self._last={}
    def classify(self,*,source,session_id,seq,source_age_ms,transport_age_ms,process_ok,max_age_ms=750.0):
        if not process_ok:
            return FreshnessDecision(Freshness.STALE,"source_not_ok",None,False)
        if not session_id:
            return FreshnessDecision(Freshness.UNKNOWN,"missing_session_id",None,False)
        if seq is None:
            return FreshnessDecision(Freshness.UNKNOWN,"missing_source_seq",None,False)
        key=(source,session_id); prev=self._last.get(key)
        if prev is not None and seq<=prev:
            return FreshnessDecision(Freshness.REPLAY,f"non_monotonic_seq:{seq}<={prev}",None,False)
        self._last[key]=seq
        if source_age_ms is None or source_age_ms<0:
            return FreshnessDecision(Freshness.UNKNOWN,"missing_or_invalid_source_age",None,False)
        if transport_age_ms is None or transport_age_ms<0:
            return FreshnessDecision(Freshness.UNKNOWN,"missing_or_invalid_transport_age",None,False)
        effective=source_age_ms+transport_age_ms
        if effective>max_age_ms:
            return FreshnessDecision(Freshness.STALE,f"effective_age>{max_age_ms:g}ms",effective,False)
        return FreshnessDecision(Freshness.FRESH,"source_and_transport_age_within_budget",effective,True)

def perception_ages(*,frame_age_ms,file_age_ms):
    # A fresh mtime cannot rejuvenate a stale captured frame.
    src=None if frame_age_ms is None else float(frame_age_ms)
    return src,max(0.0,float(file_age_ms))
