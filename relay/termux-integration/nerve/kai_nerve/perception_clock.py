"""Same-device monotonic evidence; file mtime is not an observation clock."""
import math,time
from pathlib import Path
try:BOOT_ID=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
except OSError:BOOT_ID=None
TIMING_KEYS=('boot_id','session_id','captured_mono_s','published_mono_s','detection_observed_mono_s','detection_seq')
def health(p,max_age_ms=750,*,now=None,boot_id=None):
    now=time.monotonic() if now is None else now
    expected=BOOT_ID if boot_id is None else boot_id
    def age(key):
        v=p.get(key)
        if type(v) not in (int,float) or not math.isfinite(v) or v<0 or v>now:return None
        return (now-v)*1000
    cap=age('captured_mono_s');pub=age('published_mono_s');det=age('detection_observed_mono_s')
    base=bool(expected and p.get('boot_id')==expected and isinstance(p.get('session_id'),str) and p.get('session_id') and type(p.get('seq')) is int and p['seq']>=0 and p.get('ok') is True)
    fresh=bool(base and cap is not None and pub is not None and 0<=pub<=cap<=max_age_ms)
    detection_fresh=bool(fresh and det is not None and cap<=det<=max_age_ms and type(p.get('detection_seq')) is int and p['detection_seq']<=p['seq'])
    return {'fresh':fresh,'frame_fresh':fresh,'detection_fresh':detection_fresh,'frame_age_ms':cap,'publication_age_ms':pub,'detection_age_ms':det,'freshness_reason':'recent_capture' if fresh else 'missing_invalid_or_expired_capture','actuation_allowed':False}

def parse_frame_sequence(value):
    if not isinstance(value,str) or not value or not value.isascii() or not value.isdecimal():raise ValueError('missing_or_invalid_frame_sequence')
    seq=int(value)
    if seq>9007199254740991:raise ValueError('frame_sequence_overflow')
    return seq
