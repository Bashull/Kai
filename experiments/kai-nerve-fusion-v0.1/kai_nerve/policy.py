from dataclasses import dataclass
from typing import Any

@dataclass
class PolicyContext:
    armed:bool; control_owner_valid:bool; gameplay:bool; freshness:str
    calibrated:bool; terrain_safe:bool; threat:dict[str,Any]|None=None
@dataclass
class Decision:
    allowed:bool; skill:str|None; reason:str; dry_run:bool=True

class PolicyEngine:
    def decide(self,c):
        t=c.threat or {}
        if not c.gameplay:return Decision(False,None,"not_in_gameplay")
        if c.freshness!="fresh":return Decision(False,None,f"freshness_{c.freshness}")
        if not t:return Decision(False,None,"no_threat")
        kind=str(t.get("typeId") or t.get("class") or "").lower()
        skill="flee_creeper" if "creeper" in kind else "escape_unknown"
        if not c.armed:return Decision(False,skill,"not_armed")
        if not c.control_owner_valid:return Decision(False,skill,"control_owner_invalid")
        if not c.calibrated:return Decision(False,skill,"movement_uncalibrated")
        if not c.terrain_safe:return Decision(False,skill,"escape_corridor_unverified")
        return Decision(True,skill,"preconditions_satisfied",True)
