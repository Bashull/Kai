"""Re-evaluate historical envelopes before use. No permission is persisted."""
import math, secrets, time
CLOCK_INSTANCE=secrets.token_hex(16)
def at_consumption(e, *, now_mono_ms=None):
    d=e.to_dict() if hasattr(e,'to_dict') else dict(e)
    d['freshness_at_ingest']=d.get('freshness')
    d['actuation_eligible']=False
    age=d.get('effective_age_ms'); origin=d.get('receipt_monotonic_ms')
    now=time.monotonic()*1000 if now_mono_ms is None else now_mono_ms
    nums=(age,origin,now,d.get('max_age_ms',750))
    if d.get('clock_instance') != CLOCK_INSTANCE or any(type(x) not in (int,float) or not math.isfinite(x) or x<0 for x in nums) or now<origin:
        d.update(freshness='unknown',fresh_reason='clock_or_age_unavailable_at_consumption')
        return d
    d['effective_age_ms']=age+now-origin
    if d.get('freshness')=='fresh' and d['effective_age_ms']>d.get('max_age_ms',750):
        d.update(freshness='stale',fresh_reason='expired_at_consumption')
    # Eligibility is a diagnostic only, never a physical driver permission.
    d['actuation_eligible']=bool(getattr(e,'actuation_eligible',False) and d['freshness']=='fresh')
    return d
