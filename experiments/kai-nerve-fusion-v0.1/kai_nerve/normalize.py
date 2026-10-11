from __future__ import annotations
from .models import EventEnvelope,now_ms,stable_event_id
from .freshness import SequenceTracker

class Normalizer:
    def __init__(self,max_age_ms=750.0):
        self.tracker=SequenceTracker();self.max_age_ms=float(max_age_ms)
    def normalize(self,obs,*,received_wall_ms=None,published_wall_ms=None,
                  source_age_ms=None,transport_age_ms=None,process_ok=True):
        received=now_ms() if received_wall_ms is None else float(received_wall_ms)
        published=received if published_wall_ms is None else float(published_wall_ms)
        if source_age_ms is None and obs.observed_wall_ms is not None:
            source_age_ms=max(0.0,received-float(obs.observed_wall_ms))
        if transport_age_ms is None: transport_age_ms=max(0.0,published-received)
        d=self.tracker.classify(source=obs.source,session_id=obs.session_id,seq=obs.source_seq,
            source_age_ms=source_age_ms,transport_age_ms=transport_age_ms,
            process_ok=process_ok,max_age_ms=self.max_age_ms)
        return EventEnvelope(stable_event_id(obs.source,obs.session_id,obs.source_seq,obs.kind,obs.payload),
            "kai.nerve.event.v1",obs.source,obs.kind,obs.session_id,obs.source_seq,
            obs.observed_wall_ms,obs.observed_tick,received,published,source_age_ms,transport_age_ms,
            d.effective_age_ms,d.freshness,d.reason,d.allow_actuation,obs.payload,obs.provenance or {})
