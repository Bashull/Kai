from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class PolicyContext:
    armed:bool;control_owner_valid:bool;gameplay:bool;freshness:str;provenance_level:int;sensor_authenticated:bool;calibrated:bool;terrain_safe:bool;threat:dict|None=None; observation:object|None=None
@dataclass(frozen=True)
class Decision:
    allowed:bool;skill:str|None;reason:str;dry_run:bool=True
class PolicyEngine:
    def decide(self,c:PolicyContext)->Decision:
        if not c.gameplay:return Decision(False,None,'not_in_gameplay')
        from .consumption import at_consumption
        if c.observation is None: return Decision(False,None,'observation_required_at_consumption')
        current=at_consumption(c.observation)
        if current['freshness']!='fresh': return Decision(False,None,'observation_'+current['freshness'])
        if not current.get('actuation_eligible'):return Decision(False,None,'observation_not_eligible')
        if c.freshness!='fresh':return Decision(False,None,'freshness_'+c.freshness)
        if c.provenance_level<40:return Decision(False,None,'provenance_below_engine_boundary')
        if not c.sensor_authenticated:return Decision(False,None,'sensor_not_authenticated')
        t=c.threat or {}
        if not t:return Decision(False,None,'no_threat')
        kind=str(t.get('typeId') or t.get('class') or '').lower(); skill='flee_creeper' if 'creeper' in kind else 'escape_unknown'
        if not c.armed:return Decision(False,skill,'not_armed')
        if not c.control_owner_valid:return Decision(False,skill,'control_owner_invalid')
        if not c.calibrated:return Decision(False,skill,'movement_uncalibrated')
        if not c.terrain_safe:return Decision(False,skill,'escape_corridor_unverified')
        return Decision(True,skill,'preconditions_satisfied',True)
