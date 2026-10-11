"""Pure bounded scheduling policy for 429/503; never perform requests here."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import math

def retry_after_seconds(value, now=None):
    if value is None: return None
    value=str(value).strip()
    if not value: return None
    try:
        secs=float(value)
        if math.isfinite(secs) and secs>=0: return min(3600.,secs)
    except ValueError: pass
    try:
        date=parsedate_to_datetime(value)
        if date.tzinfo is None: date=date.replace(tzinfo=timezone.utc)
        now=now or datetime.now(timezone.utc)
        return max(0., min(3600.,(date-now).total_seconds()))
    except (TypeError,ValueError,OverflowError): return None

def decide_retry(status, attempt, header=None, seed=0.5, max_attempts=8):
    if not isinstance(attempt,int) or attempt<0: raise ValueError('BAD_ATTEMPT')
    if not 0<=seed<=1: raise ValueError('BAD_JITTER')
    retriable=status in (408,425,429,500,502,503,504)
    if not retriable: return {'retry':False,'reason':'NON_RETRYABLE','wait_ms':0}
    if attempt>=max_attempts: return {'retry':False,'reason':'RETRY_BUDGET_EXHAUSTED','wait_ms':0}
    server=retry_after_seconds(header)
    backoff=min(60., (2**min(attempt,8)) * (0.75+seed*0.5))
    wait=max(backoff,server or 0.)
    return {'retry':True,'reason':'SERVER_RETRY_AFTER' if server is not None else 'LOCAL_BACKOFF',
            'wait_ms':round(wait*1000),'inventory_terminated':False}
