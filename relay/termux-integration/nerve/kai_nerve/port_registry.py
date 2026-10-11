from __future__ import annotations
from dataclasses import dataclass,asdict
@dataclass(frozen=True)
class PortClaim:
    service:str;role:str;port:int;protocol:str='tcp';owner:str='kai-nerve'
class PortRegistry:
    def __init__(self,claims=()):self.claims=[];[self.add(c) for c in claims]
    def add(self,c:PortClaim):
        if not 1024<=int(c.port)<=65535:raise ValueError('invalid_port')
        for x in self.claims:
            if (x.protocol,x.port)==(c.protocol,c.port) and x.service!=c.service:raise RuntimeError(f'port_collision:{c.protocol}:{c.port}:{x.service}:{c.service}')
        if c.role in {'minecraft_ingress','worldbus','physical_actuator'}:
            for x in self.claims:
                if x.role==c.role and x.service!=c.service:raise RuntimeError(f'role_collision:{c.role}:{x.service}:{c.service}')
        self.claims.append(c)
    def snapshot(self):return [asdict(x) for x in self.claims]
