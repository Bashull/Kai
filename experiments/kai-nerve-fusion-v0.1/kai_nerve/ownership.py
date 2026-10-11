from __future__ import annotations
import contextlib,fcntl,json,os,pathlib,secrets,time
from dataclasses import dataclass
@dataclass
class Lease:
 owner:str;lease_id:str;expires_wall_ms:float
class ControlOwnership:
 """Cross-process exclusive lease for the single physical-control owner."""
 def __init__(self,path):
  self.path=pathlib.Path(path);self.guard=self.path.with_suffix(self.path.suffix+".lock")
  self.path.parent.mkdir(parents=True,exist_ok=True)
 @contextlib.contextmanager
 def _locked(self,exclusive=True):
  self.guard.parent.mkdir(parents=True,exist_ok=True)
  with self.guard.open("a+") as f:
   fcntl.flock(f.fileno(),fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
   try:yield
   finally:fcntl.flock(f.fileno(),fcntl.LOCK_UN)
 def _read_unlocked(self):
  try:return json.loads(self.path.read_text())
  except Exception:return None
 def acquire(self,owner,ttl_s=30.0,now_ms=None):
  now=time.time()*1000 if now_ms is None else float(now_ms)
  with self._locked(True):
   cur=self._read_unlocked()
   if cur and float(cur.get("expires_wall_ms",0))>now and cur.get("owner")!=owner:
    raise RuntimeError(f"control_owned_by:{cur.get('owner')}")
   lease=Lease(owner,secrets.token_urlsafe(12),now+ttl_s*1000)
   tmp=self.path.with_suffix(self.path.suffix+".tmp");tmp.write_text(json.dumps(lease.__dict__,sort_keys=True))
   os.replace(tmp,self.path);return lease
 def valid(self,lease,now_ms=None):
  now=time.time()*1000 if now_ms is None else float(now_ms)
  with self._locked(False):
   cur=self._read_unlocked()
   return bool(cur and cur.get("owner")==lease.owner and cur.get("lease_id")==lease.lease_id and float(cur.get("expires_wall_ms",0))>now)
 def release(self,lease):
  with self._locked(True):
   cur=self._read_unlocked()
   if cur and cur.get("owner")==lease.owner and cur.get("lease_id")==lease.lease_id:
    try:self.path.unlink()
    except FileNotFoundError:pass
