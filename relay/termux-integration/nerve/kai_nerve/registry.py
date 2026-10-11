from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class Component:
    name:str; role:str; owner:str; capabilities:tuple[str,...]=()
class ComponentRegistry:
    SINGLE_OWNER_ROLES={'minecraft_ingress','physical_actuator','worldbus_writer'}
    def __init__(self):self.items={}
    def register(self,c:Component):
        key=(c.role,c.name)
        if key in self.items: raise RuntimeError('duplicate_component')
        if c.role in self.SINGLE_OWNER_ROLES:
            owners={x.owner for x in self.items.values() if x.role==c.role}
            if owners and c.owner not in owners: raise RuntimeError(f'role_already_owned:{c.role}:{sorted(owners)}')
        self.items[key]=c
    def snapshot(self):return [c.__dict__ for c in self.items.values()]
