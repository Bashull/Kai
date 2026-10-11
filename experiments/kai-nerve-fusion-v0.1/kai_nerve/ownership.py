from __future__ import annotations
import json,os,pathlib,secrets,time
from dataclasses import dataclass

@dataclass
class Lease:
    owner:str; lease_id:str; expires_wall_ms:float

class ControlOwnership:
    def __init__(self,path):
        self.path=pathlib.Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
    def _read(self):
        try:return json.loads(self.path.read_text())
        except Exception:return None
    def acquire(self,owner,ttl_s=30.0,now_ms=None):
        now=time.time()*1000 if now_ms is None else float(now_ms);cur=self._read()
        if cur and float(cur.get("expires_wall_ms",0))>now and cur.get("owner")!=owner:
            raise RuntimeError(f"control_owned_by:{cur.get('owner')}")
        lease=Lease(owner,secrets.token_urlsafe(12),now+ttl_s*1000)
        tmp=self.path.with_suffix(".tmp");tmp.write_text(json.dumps(lease.__dict__,sort_keys=True))
        os.replace(tmp,self.path);return lease
    def valid(self,lease,now_ms=None):
        now=time.time()*1000 if now_ms is None else float(now_ms);cur=self._read()
        return bool(cur and cur.get("owner")==lease.owner and cur.get("lease_id")==lease.lease_id
                    and float(cur.get("expires_wall_ms",0))>now)
    def release(self,lease):
        if self.valid(lease):
            try:self.path.unlink()
            except FileNotFoundError:pass
