from dataclasses import dataclass,asdict
@dataclass(frozen=True)
class Skill:
    name:str;mode:str;risk:str;owner_role:str;preconditions:tuple[str,...];abort_if:tuple[str,...];success:tuple[str,...];max_duration_s:float;cooldown_s:float;observability:tuple[str,...]
SKILLS={
'verify_engine_boundary':Skill('verify_engine_boundary','read_only','low','minecraft_ingress',('PID-filtered Minecraft logcat','protocol v4','sensor session_id+strict seq','fresh timestamps','challenge match'),('Minecraft PID changes','transport loses PID binding','session reset mid-proof'),('same event_id persisted and read back from WorldBus with engine_boundary provenance',),8,0,('event_id','collector_instance','minecraft_pid','session_id','seq','effective_age_ms')),
'scan_safe':Skill('scan_safe','read_only','low','sensor',('fresh evidence','gameplay context known'),('source stale','session changes','scan_error'),('hazards classified or unknown recorded',),2,0,('entity ids','typeIds','relative vectors','scan_error')),
'flee_creeper':Skill('flee_creeper','physical-plan-only','high','physical_actuator',('engine_boundary provenance','fresh non-replay','armed lease','single actuator owner','movement calibration','terrain corridor verified','independent reviewer no veto'),('stale/unknown/replay','HUD exit','cliff/lava unknown','ownership lost','death','session changes','review veto'),('distance increasing','critical radius exited','traversable terrain retained'),1.5,2.5,('decision_id','skill_version','input_event_id','lease_token_hash','distance_before_after','abort_reason')),
'escape_unknown':Skill('escape_unknown','physical-plan-only','high','physical_actuator',('engine_boundary damage/threat evidence','safe retreat vector','terrain corridor verified','armed lease','independent reviewer no veto'),('stale/replay','no safe vector','ownership lost','review veto'),('damage stops','distance increases or shelter reached'),1.2,2,('decision_id','unknown_entity_track','input_event_id','result')),
'audit_runtime_identity':Skill('audit_runtime_identity','read_only','low','runtime_auditor',('service exists',),(),('run script, PID, cmdline, cwd, redacted env, target identities and listener snapshot recorded',),5,0,('runtime_identity_sha256','target_identity_match','ports')),
'replay_incident':Skill('replay_incident','read_only','low','analyst',('event log exists','source lock known'),(),('timeline reconstructed with stale/unknown gaps explicit',),30,0,('event ids','timestamps','freshness','provenance','gaps')),
}
def skill_list():return [asdict(SKILLS[k]) for k in sorted(SKILLS)]
