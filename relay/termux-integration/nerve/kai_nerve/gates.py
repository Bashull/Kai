from __future__ import annotations
from dataclasses import dataclass,asdict
@dataclass(frozen=True)
class GateInput:
    tests_pass:bool=False
    static_sensor_ok:bool=False
    runtime_identity_captured:bool=False
    runtime_target_match:bool=False
    bridge_contract_clean:bool=False
    freshness_vector_verified:bool=False
    engine_boundary_event:bool=False
    sensor_challenge_verified:bool=False
    worldbus_persisted:bool=False
    stale_replay_tests:bool=False
    single_owner_lease:bool=False
    driver_calibrated:bool=False
    reflex_dry_run:bool=False
    rollback_ready:bool=False
    independent_review_passed:bool=False
@dataclass(frozen=True)
class GateResult:
    level:str; pass_gate:bool; blockers:tuple[str,...]
    def to_dict(self):return asdict(self)
def _missing(items):return tuple(k for k,v in items if not v)
def evaluate(i:GateInput)->GateResult:
    static=[('tests_pass',i.tests_pass),('static_sensor_ok',i.static_sensor_ok),('runtime_identity_captured',i.runtime_identity_captured),('runtime_target_match',i.runtime_target_match),('bridge_contract_clean',i.bridge_contract_clean),('freshness_vector_verified',i.freshness_vector_verified)]
    m=_missing(static)
    if m:return GateResult('static_and_runtime_identity',False,m)
    e2e=[('engine_boundary_event',i.engine_boundary_event),('sensor_challenge_verified',i.sensor_challenge_verified),('worldbus_persisted',i.worldbus_persisted),('stale_replay_tests',i.stale_replay_tests)]
    m=_missing(e2e)
    if m:return GateResult('sensor_e2e',False,m)
    act=[('single_owner_lease',i.single_owner_lease),('driver_calibrated',i.driver_calibrated),('reflex_dry_run',i.reflex_dry_run),('rollback_ready',i.rollback_ready),('independent_review_passed',i.independent_review_passed)]
    m=_missing(act)
    if m:return GateResult('actuation_readiness',False,m)
    return GateResult('actuation_readiness',True,())
