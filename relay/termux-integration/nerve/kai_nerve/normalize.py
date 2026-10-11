from __future__ import annotations
import time
from .consumption import CLOCK_INSTANCE
from .models import EventEnvelope,ParsedObservation,ProvenanceEvidence,ProvenanceLevel,now_ms,stable_event_id,Freshness
from .freshness import ReplayLedger,temporal_decision

class Normalizer:
    def __init__(self,replay:ReplayLedger,max_age_ms:float=750.0):
        self.replay=replay; self.max_age_ms=float(max_age_ms)
    def normalize(self,obs:ParsedObservation,*,evidence:ProvenanceEvidence,received_wall_ms:float|None=None,
                  published_wall_ms:float|None=None,consumed_wall_ms:float|None=None,
                  frame_age_at_publish_ms:float|None=None,detection_wall_ms:float|None=None,
                  process_ok:bool=True)->EventEnvelope:
        received=now_ms() if received_wall_ms is None else float(received_wall_ms)
        published=received if published_wall_ms is None else float(published_wall_ms)
        consumed=published if consumed_wall_ms is None else float(consumed_wall_ms)
        d=temporal_decision(session_id=obs.session_id,seq=obs.source_seq,source=f'{obs.source}|{int(evidence.level)}|{evidence.transport}',replay=self.replay,
            observed_wall_ms=obs.observed_wall_ms,received_wall_ms=received,published_wall_ms=published,consumed_wall_ms=consumed,
            frame_age_at_publish_ms=frame_age_at_publish_ms,detection_wall_ms=detection_wall_ms,process_ok=process_ok,max_age_ms=self.max_age_ms)
        prov=evidence.to_dict()
        if obs.claimed_provenance: prov['payload_claim']=obs.claimed_provenance
        sensor_authenticated=bool((evidence.evidence or {}).get('sensor_authenticated'))
        protocol=str((evidence.evidence or {}).get('protocol') or '')
        eligible=(d.freshness is Freshness.FRESH and evidence.level>=ProvenanceLevel.ENGINE_BOUNDARY and sensor_authenticated and protocol=='4' and obs.source=='minecraft.kai_nerve')
        env=EventEnvelope(stable_event_id(f'{obs.source}|{int(evidence.level)}|{evidence.transport}|{d.freshness.value}',obs.session_id,obs.source_seq,obs.kind,obs.payload),'kai.nerve.event.v3',obs.source,obs.kind,
            obs.session_id,obs.source_seq,obs.observed_wall_ms,obs.observed_tick,received,published,consumed,
            d.source_age_ms,d.publish_delay_ms,d.publication_age_ms,d.detection_age_ms,d.effective_age_ms,d.freshness,d.reason,prov,eligible,obs.payload)

        env.receipt_monotonic_ms=time.monotonic()*1000
        env.clock_instance=CLOCK_INSTANCE
        env.max_age_ms=self.max_age_ms
        return env
