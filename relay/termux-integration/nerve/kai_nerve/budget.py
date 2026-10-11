from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class BudgetSnapshot:
    tick_ms:float;own_ms:float;foreign_ms:float;headroom_ms:float;over_budget:bool
class BudgetGovernor:
    """Reserve headroom for Minecraft/add-ons instead of consuming the whole tick budget."""
    def __init__(self,tick_ms=50.0,reserve_ratio=0.35):self.tick_ms=float(tick_ms);self.reserve_ratio=float(reserve_ratio)
    def snapshot(self,own_ms,foreign_ms=0.0):
        reserve=self.tick_ms*self.reserve_ratio;used=max(0,float(own_ms))+max(0,float(foreign_ms));head=max(0,self.tick_ms-used);return BudgetSnapshot(self.tick_ms,float(own_ms),float(foreign_ms),head,head<reserve)
    def interval_multiplier(self,s:BudgetSnapshot):
        if not s.over_budget:return 1.0
        reserve=self.tick_ms*self.reserve_ratio;return min(8.0,max(1.25,reserve/max(1e-6,s.headroom_ms)))
